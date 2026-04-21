import uuid
import logging.config
import connexion
import json
from datetime import datetime, timezone
from kafka import KafkaProducer
from connexion import NoContent

from config_handler import APP_CONFIG, BROKER_CONFIG, API_CONFIG, LOG_CONFIG


def health():
    logger.debug("Received health check request")
    return (NoContent, 200)


def get_stats():
    """Returns the server's current datetime in UTC"""
    logger.debug("Received stats request")
    return ({"status_datetime": datetime.now(tz=timezone.utc).isoformat()}, 200)


async def report_energy_consumption_readings(body: dict) -> tuple[object, int]:
    # INIT
    plug_data = {
        "plug_id": body["plug_id"],
        "plug_country": body.get("plug_country", None), # Non-required field
        "plug_uptime": body["plug_uptime"],
        "batch_timestamp": body["report_timestamp"],
        "batch_trace_id": str(uuid.uuid4())
    }

    logger.debug(f"Received energy consumption report with trace id: {plug_data['batch_trace_id']}")

    if plug_data["plug_country"] is None:
        del plug_data["plug_country"]
    
    # PRODUCE MESSAGES
    for reading in body["readings"]:
        reading_data = plug_data.copy()
        reading_data.update(reading)

        message = {
            "type": "energy_consumption", 
            "datetime": datetime.now(tz=timezone.utc).isoformat(),
            "payload": reading_data
        }

        producer.send(BROKER_CONFIG["topic"], json.dumps(message).encode('utf-8'))
    
    # producer.flush()
    
    # RETURN
    logger.debug(f"Sent all readings to broker for event {plug_data['batch_trace_id']}")
    return (NoContent, 201)


async def report_internal_temp_readings(body: dict) -> tuple[object, int]:
    # INIT
    plug_data = {
        "plug_id": body["plug_id"],
        "plug_country": body.get("plug_country", None), # Non-required field
        "plug_uptime": body["plug_uptime"],
        "batch_timestamp": body["report_timestamp"],
        "batch_trace_id": str(uuid.uuid4())
    }

    if plug_data["plug_country"] is None:
        del plug_data["plug_country"]

    logger.debug(f"Received internal temperature report with trace id: {plug_data['batch_trace_id']}")

    # PRODUCE MESSAGES
    for reading in body["readings"]:
        reading_data = plug_data.copy()
        reading_data.update(reading)

        message = {
            "type": "internal_temperature", 
            "datetime": datetime.now(tz=timezone.utc).isoformat(),
            "payload": reading_data
        }

        producer.send(BROKER_CONFIG["topic"], json.dumps(message).encode('utf-8'))
    
    # producer.flush()
    
    # RETURN
    logger.debug(f"Sent all readings to broker for event {plug_data['batch_trace_id']}")
    return (NoContent, 201)


# SETUP LOGGING
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("basicLogger")


# SETUP CONNEXION APP
app = connexion.FlaskApp(__name__, specification_dir=API_CONFIG["spec_dir"])
app.add_api(API_CONFIG["file"], 
            strict_validation=API_CONFIG["strict_validation"], 
            validate_responses=API_CONFIG["validate_responses"],
            base_path=API_CONFIG["base_path"])


# SETUP KAFKA PRODUCER
producer = KafkaProducer(bootstrap_servers=f"{BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}")


# GO GO GO
if __name__ == "__main__":
    app.run(port=APP_CONFIG["port"], host=APP_CONFIG["host"])