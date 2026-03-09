import logging.config
import connexion
import json

from kafka import KafkaConsumer
from connexion import NoContent
from pathlib import Path

from config_handler import APP_CONFIG, API_CONFIG, BROKER_CONFIG, LOG_CONFIG


##### ENDPOINTS #####
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
    logger.debug(f"Starting broker seeking for event type '{event_type}' at index {index}")

    # init
    consumer = get_consumer()
    index_counter = -1

    # get messages
    for msg in consumer:
        message_str = msg.value.decode("utf-8")
        message = json.loads(message_str)

        # count if message is right type
        if message["type"] == event_type:
            index_counter += 1

            # return if target index is hit
            if index_counter == index:
                logger.info(f"Found event index {index} for event '{event_type}' in Kafka.")
                return message
    
    # give up
    logger.warning(f"Couldn't find event index {index} for event '{event_type}' in Kafka. Max index for this event type is {index_counter}")
    return None


def count_events() -> dict:
    logger.debug("Starting event counting")

    # init
    consumer = get_consumer()
    counts = {}

    # get messages
    for msg in consumer:
        message_str = msg.value.decode("utf-8")
        message = json.loads(message_str)

        # increment count for this message type
        counts[message["type"]] = counts.get(message["type"], 0) + 1
    
    logger.info(f"Finished counting events in Kafka. Counts: {counts}")
    return counts


def get_consumer() -> KafkaConsumer:
    consumer = KafkaConsumer(
        BROKER_CONFIG["topic"],
        bootstrap_servers=f"{BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}",
        #group_id=BROKER_CONFIG["group_id"],
        auto_offset_reset="earliest",
        consumer_timeout_ms = 1000
    )

    logger.debug(f"Connected to broker at {BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}, subscribed to topic '{BROKER_CONFIG['topic']}'")
    return consumer


##### INIT #####
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("basicLogger")


app = connexion.FlaskApp(__name__, specification_dir=API_CONFIG["spec_dir"])
app.add_api(API_CONFIG["file"], 
            strict_validation=API_CONFIG["strict_validation"], 
            validate_responses=API_CONFIG["validate_responses"])


if __name__ == "__main__":
    app.run(port=APP_CONFIG["port"], host=APP_CONFIG["host"])