from logging import getLogger
from time import sleep
from kafka import KafkaConsumer
from kafka.structs import OffsetAndMetadata
from kafka.errors import KafkaError
from config_handler import APP_CONFIG, BROKER_CONFIG


logger = getLogger("basicLogger")


def build_consumer(subscribe_to_topic: bool = True) -> KafkaConsumer:
    try:
        consumer = KafkaConsumer(
            *[BROKER_CONFIG["topic"]] if subscribe_to_topic else [],
            bootstrap_servers=f"{BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}",
            group_id=BROKER_CONFIG["group_id"],
            enable_auto_commit=False,
        )

        logmsg = f"Connected to broker at {BROKER_CONFIG['host']}:{BROKER_CONFIG['port']}"
        logmsg += f", subscribed to topic '{BROKER_CONFIG['topic']}'" if subscribe_to_topic else ""
        logger.info(logmsg)

        return consumer
    
    except KafkaError as e:
        logger.error(f"Error building Kafka consumer: {e}")
        return None

# I overcomplicated this whole thing
def commit_offsets_with_retry(consumer: KafkaConsumer, offsets_to_commit: dict) -> KafkaConsumer | None:
    if not offsets_to_commit:
        return consumer

    offsets_to_commit = {topic_partition: OffsetAndMetadata(*latest_offset) for topic_partition, latest_offset in offsets_to_commit.items()}
    try:
        consumer.commit(offsets=offsets_to_commit)
        return consumer
    except KafkaError as e:
        logger.error(f"Kafka error while committing offsets. Retrying with fresh consumer. Error: {e}")

    try:
        consumer.close(autocommit=False)
    except KafkaError:
        pass

    recovery_consumer = build_consumer(subscribe_to_topic=False)

    while True:
        if recovery_consumer is None:
            logger.error(f"Unable to connect to broker with recovery consumer. Retrying in {APP_CONFIG['db']['retry_interval_secs']} seconds.")
            sleep(APP_CONFIG["db"]["retry_interval_secs"])

            recovery_consumer = build_consumer(subscribe_to_topic=False)
            continue

        try:
            recovery_consumer.assign(list(offsets_to_commit.keys()))
            recovery_consumer.commit(offsets=offsets_to_commit)
            logger.info("Recovered offset commit using fresh consumer.")

            recovery_consumer.close(autocommit=False)
            return None

        except KafkaError as e:
            logger.error(f"Recovery consumer failed to commit offsets. Retrying in {APP_CONFIG['db']['retry_interval_secs']} seconds. Error: {e}")

            try:
                recovery_consumer.close(autocommit=False)
            except KafkaError:
                pass
            
            recovery_consumer = None