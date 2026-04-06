import connexion
import json
import logging.config

from time import sleep, monotonic
from datetime import datetime
from threading import Thread

from sqlalchemy import select, insert
from sqlalchemy.orm import Session as _Type_SQLAlchemySession
from sqlalchemy.exc import DBAPIError

from db_utils import use_db_session
from kafka_utils import build_consumer, commit_offsets_with_retry
from models import EnergyConsumedReading, InternalTempReading
from config_handler import APP_CONFIG, BROKER_CONFIG, API_CONFIG, LOG_CONFIG


def consume_broker_messages():
    logger.debug("Starting broker consumer thread...")

    energy_consumption_messages = []
    temperature_reading_messages = []
    latest_offsets: dict = {}
    last_batch_time = monotonic()
    consumer = build_consumer()

    while True:
        # Make sure consumer is OK
        if consumer is None:
            logger.error(f"Unable to connect to broker. Retrying in {APP_CONFIG['db']['retry_interval_secs']} seconds.")
            sleep(APP_CONFIG["db"]["retry_interval_secs"])

            consumer = build_consumer()
            continue
        
        # Get messages
        try:
            records = consumer.poll(timeout_ms=1000, max_records=BROKER_CONFIG["max_batch_size"])
        except Exception as e:
            # Consumer ain't OK
            logger.error(f"Error occurred while polling messages from broker: {e}")

            try:
                consumer.close(autocommit=False)
            except Exception:
                pass
            
            consumer = None
            continue

        # You've got mail!
        for topic_partition, record_batch in records.items():
            for msg in record_batch:
                message_str = msg.value.decode("utf-8")
                message = json.loads(message_str)
                payload = message.get("payload", {})

                # Put message into appropriate buffer
                if message["type"] == "energy_consumption":
                    energy_consumption_messages.append(payload)
                elif message["type"] == "internal_temperature":
                    temperature_reading_messages.append(payload)
                else:
                    # Wtf did I just eat?
                    logger.warning(f"Consumed message with unknown type '{message['type']}': {message}")

                logger.debug(f"Consumed message from broker: {message}")
                latest_offsets[topic_partition] = (msg.offset + 1, msg.timestamp, msg.leader_epoch)

        # Check if it's time to commit
        buffer_size = len(energy_consumption_messages) + len(temperature_reading_messages)
        buffer_full = buffer_size >= BROKER_CONFIG["max_batch_size"]
        buffer_expiring = (monotonic() - last_batch_time) >= BROKER_CONFIG["max_batch_age_ms"] / 1000

        # It's tiiiiiiiiiiiiiime! 🧊
        if (buffer_full or buffer_expiring) and buffer_size > 0:
            logger.info(f"Committing {buffer_size} messages to database.")

            db_commit_success = False
            while not db_commit_success:
                db_commit_success = commit_buffers(
                    energy_buffer=energy_consumption_messages, 
                    temperature_buffer=temperature_reading_messages
                )

                if db_commit_success:
                    consumer = commit_offsets_with_retry(consumer, latest_offsets.copy())

                    energy_consumption_messages.clear()
                    temperature_reading_messages.clear()
                    latest_offsets.clear()
                    last_batch_time = monotonic()

                else:
                    logger.error(f"Unable to communicate with database! Retrying in {APP_CONFIG['db']['retry_interval_secs']} seconds...")

                    try:
                        assigned = consumer.assignment()
                        consumer.pause(*(assigned if assigned else [])) # Pause consumption while we wait for the DB to hopefully come back up
                        consumer.poll(timeout_ms=APP_CONFIG["db"]["retry_interval_secs"] * 1000) # Wait before retrying but tell kafka we're alive
                        consumer.resume(*(assigned if assigned else [])) # Resume consumption once we're ready to try again

                    except Exception as e:
                        logger.error(f"Error occurred while pausing/resuming consumer during DB retry wait: {e}")

                        try:
                            consumer.close(autocommit=False)
                        except Exception:
                            pass

                        consumer = None # Force a full consumer rebuild on the next loop iteration


def health():
    logger.debug("Received health check request")
    return (connexion.NoContent, 200)


@use_db_session
def commit_buffers(session: _Type_SQLAlchemySession, energy_buffer: list[dict], temperature_buffer: list[dict]) -> bool:
    try:
        if energy_buffer:
            session.execute(
                insert(EnergyConsumedReading),
                energy_buffer
            )

        if temperature_buffer:
            session.execute(
                insert(InternalTempReading),
                temperature_buffer
            )

        session.commit()

    except DBAPIError as e:
        session.rollback()
        logger.error(f"Failed to store batch in the database. Error: {e}")
        return False
    
    return True


@use_db_session
def get_energy_consumption_readings(session: _Type_SQLAlchemySession, start_timestamp: str, end_timestamp: str) -> tuple[object, int]:
    query = select(EnergyConsumedReading).where(
        EnergyConsumedReading.date_created >= datetime.fromisoformat(start_timestamp),
        EnergyConsumedReading.date_created < datetime.fromisoformat(end_timestamp)
    )

    try:
        readings = session.execute(query).scalars().all()
    except DBAPIError as e:
        logger.error(f"Failed to retrieve energy consumption readings from the database. Error: {e}")
        return ({"error": "Failed to retrieve energy consumption readings from the database."}, 500)

    logger.debug(f"Retrieved {len(readings)} energy consumption readings created between {start_timestamp} and {end_timestamp}")

    return ([r.as_dict() for r in readings], 200)


@use_db_session
def get_internal_temp_readings(session: _Type_SQLAlchemySession, start_timestamp: str, end_timestamp: str) -> tuple[object, int]:
    query = select(InternalTempReading).where(
        InternalTempReading.date_created >= datetime.fromisoformat(start_timestamp),
        InternalTempReading.date_created < datetime.fromisoformat(end_timestamp)
    )

    try:
        readings = session.execute(query).scalars().all()
    except DBAPIError as e:
        logger.error(f"Failed to retrieve internal temperature readings from the database. Error: {e}")
        return ({"error": "Failed to retrieve internal temperature readings from the database."}, 500)

    logger.debug(f"Retrieved {len(readings)} internal temperature readings created between {start_timestamp} and {end_timestamp}")

    return ([r.as_dict() for r in readings], 200)


# SETUP LOGGING
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("basicLogger")


# SETUP CONNEXION APP
app = connexion.FlaskApp(__name__, specification_dir=API_CONFIG["spec_dir"])
app.add_api(API_CONFIG["file"], 
            strict_validation=API_CONFIG["strict_validation"], 
            validate_responses=API_CONFIG["validate_responses"])


# GO GO GO
if __name__ == "__main__":
    if APP_CONFIG["auto_create_tables"]:
        from db_utils import create_all_tables

        success = False
        while not success:
            try:
                success = create_all_tables() # metadata.create_all() checks first by default, so this SHOULD be safe
                logger.info("Ensured all tables are created in the database.")

            except DBAPIError as e:
                logger.error(f"Failed to create tables in the database on startup. Retrying in {APP_CONFIG['db']['retry_interval_secs']} seconds. Error: {e}")
                sleep(APP_CONFIG["db"]["retry_interval_secs"])
    
    consumer_thread = Thread(target=consume_broker_messages, daemon=True)
    consumer_thread.start()
    
    app.run(port=APP_CONFIG["port"], host=APP_CONFIG["host"])