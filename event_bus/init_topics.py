from __future__ import annotations

import asyncio
import logging
import os

from aiokafka.admin import AIOKafkaAdminClient, NewPartitions, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

from event_bus.topics import KAFKA_TOPICS, KafkaTopicSpec

logger = logging.getLogger(__name__)


async def ensure_topics(bootstrap_servers: str) -> None:
    admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap_servers)
    await admin.start()
    try:
        existing_topics = await admin.list_topics()
        for topic in KAFKA_TOPICS:
            if topic.name not in existing_topics:
                await _create_topic(admin, topic)
                continue

            current_partitions = await _partition_count(admin, topic.name)
            if current_partitions < topic.partitions:
                await admin.create_partitions(
                    {topic.name: NewPartitions(total_count=topic.partitions)}
                )
                logger.info(
                    "Kafka topic partitions increased: topic=%s from=%s to=%s",
                    topic.name,
                    current_partitions,
                    topic.partitions,
                )
            elif current_partitions > topic.partitions:
                logger.warning(
                    "Kafka topic has more partitions than contract: "
                    "topic=%s current=%s contract=%s",
                    topic.name,
                    current_partitions,
                    topic.partitions,
                )
            else:
                logger.info(
                    "Kafka topic already exists: topic=%s partitions=%s",
                    topic.name,
                    topic.partitions,
                )
    finally:
        await admin.close()


async def _create_topic(admin: AIOKafkaAdminClient, topic: KafkaTopicSpec) -> None:
    try:
        await admin.create_topics(
            [
                NewTopic(
                    name=topic.name,
                    num_partitions=topic.partitions,
                    replication_factor=topic.replication_factor,
                )
            ],
            validate_only=False,
        )
        logger.info(
            "Kafka topic created: topic=%s partitions=%s replication_factor=%s",
            topic.name,
            topic.partitions,
            topic.replication_factor,
        )
    except TopicAlreadyExistsError:
        logger.info("Kafka topic already exists: topic=%s", topic.name)


async def _partition_count(admin: AIOKafkaAdminClient, topic_name: str) -> int:
    descriptions = await admin.describe_topics([topic_name])
    description = descriptions[0]
    if isinstance(description, dict):
        return len(description["partitions"])
    return len(description.partitions)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is required to initialize Kafka topics")
    asyncio.run(ensure_topics(bootstrap_servers))


if __name__ == "__main__":
    main()
