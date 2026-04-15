import json
import logging.config
from threading import Thread
from pathlib import Path
from time import sleep

import connexion
from connexion import NoContent
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer, TopicPartition

import message_cache
from config_handler import APP_CONFIG, API_CONFIG, BROKER_CONFIG, LOG_CONFIG


##### MESSAGE CACHE #####
# Importing from message_cache module so that it's shared across all threads and functions in this app
MESSAGES = message_cache.MESSAGES


##### ENDPOINTS #####
def health():
    logger.debug("Received health check request")
    return (NoContent, 200)


def get_energy_event(index: int):
    logger.debug(f"Received request for energy event at index {index}")

    found_event = seek_for_event("energy_consumption", index)

    if found_event is not None:
        return (found_event["payload"], 200)
    
    return (NoContent, 404)


def get_temperature_event(index: int):
    logger.debug(f"Received request for temperature event at index {index}")

    found_event = seek_for_event("internal_temperature", index)

    if found_event is not None:
        return (found_event["payload"], 200)
    
    return (NoContent, 404)


def get_stats():
    logger.debug("Received request for event stats")

    event_counts = count_events()

    response = {
        "num_energy_events": event_counts.get("energy_consumption", 0),
        "num_temperature_events": event_counts.get("internal_temperature", 0)
    }

    return (response, 200)


##### UTILS #####
def seek_for_event(event_type: str, index: int) -> dict | None:
    logger.debug(f"Checking message cache for event type '{event_type}' at index {index}")

    # grab the cache list for this event type, or an empty list if it doesn't exist
    event_cache = MESSAGES.get(event_type, [])

    try:
        # try to grab the requested message
        message = event_cache[index]
        logger.info(f"Found event index {index} for event '{event_type}' in message cache.")

        # return it
        return message
    except IndexError:
        logger.warning(f"Couldn't find event index {index} for event '{event_type}' in message cache. Max index for this event type is {len(event_cache) - 1}.")
        return None


def count_events() -> dict:
    counts = {
        "energy_consumption": len(MESSAGES.get("energy_consumption", [])),
        "internal_temperature": len(MESSAGES.get("internal_temperature", []))
    }
    
    logger.info(f"Returned event counts from Kafka message cache. Counts: {counts}")
    return counts


def consume_all_messages():
    logger.debug("Starting broker consumer thread...")

    # connect to the broker
    consumer = KafkaConsumer(
        bootstrap_servers=f"{BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}",
        auto_offset_reset="earliest",
    )

    logger.info(f"Connected to broker at {BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}")

    # get all partition ids
    partition_ids = consumer.partitions_for_topic(BROKER_CONFIG["topic"]) or None

    while not partition_ids:
        if partition_ids is None:
            logger.warning(f"Topic '{BROKER_CONFIG['topic']}' does not exist on broker. Retrying every 5 seconds...")
        
        sleep(5)
        partition_ids = consumer.partitions_for_topic(BROKER_CONFIG["topic"])
    
    logger.debug(f"Fetched partition ids for topic '{BROKER_CONFIG['topic']}': {partition_ids}")

    # subscribe to all partitions and seek to beginning
    consumer.assign([TopicPartition(BROKER_CONFIG["topic"], part_id) for part_id in partition_ids])
    consumer.seek_to_beginning()

    logger.info(f"Subscribed to all {len(partition_ids)} partitions for topic '{BROKER_CONFIG['topic']}'")
    
    # c o n s u m e
    for msg in consumer:
        message_str = msg.value.decode("utf-8")
        message = json.loads(message_str)

        logger.debug(f"Received message from broker: {message}")

        if message["type"] in MESSAGES:
            MESSAGES[message["type"]].append(message)
        else:
            MESSAGES[message["type"]] = [message]


##### INIT #####
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("basicLogger")


app = connexion.FlaskApp(__name__, specification_dir=API_CONFIG["spec_dir"])

app.add_api(API_CONFIG["file"], 
            strict_validation=API_CONFIG["strict_validation"], 
            validate_responses=API_CONFIG["validate_responses"],
            base_path=API_CONFIG["base_path"])

app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=API_CONFIG["cors"]["allow_origins"],
    allow_methods=API_CONFIG["cors"]["allow_methods"],
    allow_headers=API_CONFIG["cors"]["allow_headers"],
    allow_credentials=True,
)


if __name__ == "__main__":
    consumer_thread = Thread(target=consume_all_messages, daemon=True)
    consumer_thread.start()

    app.run(port=APP_CONFIG["port"], host=APP_CONFIG["host"])