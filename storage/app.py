import connexion
import json
import logging.config

from datetime import datetime
from kafka import KafkaConsumer
from threading import Thread
from connexion import NoContent

from sqlalchemy import select
from sqlalchemy.orm import Session as _Type_SQLAlchemySession

from db_utils import use_db_session
from models import EnergyConsumedReading, InternalTempReading
from config_handler import APP_CONFIG, BROKER_CONFIG, API_CONFIG, LOG_CONFIG


def consume_broker_messages():
    logger.debug("Starting broker consumer thread...")

    consumer = KafkaConsumer(
        BROKER_CONFIG["topic"],
        bootstrap_servers=f"{BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}",
        group_id=BROKER_CONFIG["group_id"]
    )

    logger.info(f"Connected to broker at {BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}, subscribed to topic '{BROKER_CONFIG['topic']}'")

    for msg in consumer:
        message_str = msg.value.decode("utf-8")
        message = json.loads(message_str)
        payload = message.get("payload", {})

        logger.debug(f"Consumed message from broker: {message}")

        if message["type"] == "energy_consumption":
            store_energy_consumption_reading(body=payload)
        elif message["type"] == "internal_temperature":
            store_internal_temp_reading(body=payload)
        else:
            logger.warning(f"Consumed message with unknown type '{message['type']}': {message}")


def health():
    logger.debug("Received health check request")
    return (connexion.NoContent, 200)


@use_db_session
def store_energy_consumption_reading(session: _Type_SQLAlchemySession, body: dict):
    reading = EnergyConsumedReading(**body) # Unpacking lesgoooo

    session.add(reading)
    session.commit()

    logger.debug(f"Stored energy consumption reading for batch with trace id: {body['batch_trace_id']}")


@use_db_session
def store_internal_temp_reading(session: _Type_SQLAlchemySession, body: dict):
    reading = InternalTempReading(**body)

    session.add(reading)
    session.commit()

    logger.debug(f"Stored internal temperature reading for batch with trace id: {body['batch_trace_id']}")


@use_db_session
def get_energy_consumption_readings(session: _Type_SQLAlchemySession, start_timestamp: str, end_timestamp: str) -> tuple[object, int]:
    query = select(EnergyConsumedReading).where(
        EnergyConsumedReading.date_created >= datetime.fromisoformat(start_timestamp),
        EnergyConsumedReading.date_created < datetime.fromisoformat(end_timestamp)
    )

    readings = session.execute(query).scalars().all()

    logger.debug(f"Retrieved {len(readings)} energy consumption readings created between {start_timestamp} and {end_timestamp}")

    return ([r.as_dict() for r in readings], 200)


@use_db_session
def get_internal_temp_readings(session: _Type_SQLAlchemySession, start_timestamp: str, end_timestamp: str) -> tuple[object, int]:
    query = select(InternalTempReading).where(
        InternalTempReading.date_created >= datetime.fromisoformat(start_timestamp),
        InternalTempReading.date_created < datetime.fromisoformat(end_timestamp)
    )

    readings = session.execute(query).scalars().all()

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
        create_all_tables() # metadata.create_all() checks first by default, so this SHOULD be safe
    
    consumer_thread = Thread(target=consume_broker_messages, daemon=True)
    consumer_thread.start()
    
    app.run(port=APP_CONFIG["port"], host=APP_CONFIG["host"])