import asyncio
import logging
from collections.abc import Sequence

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from auto_parking.ports.events import EventEnvelope, EventHandler

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None
        self._lock = asyncio.Lock()

    async def publish(
        self,
        topic: str,
        event: EventEnvelope,
        *,
        key: str | None = None,
    ) -> None:
        producer = await self._ensure_started()
        await producer.send_and_wait(
            topic,
            event.to_json().encode("utf-8"),
            key=key.encode("utf-8") if key else None,
        )

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def _ensure_started(self) -> AIOKafkaProducer:
        async with self._lock:
            if self._producer is None:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self._bootstrap_servers,
                )
                await self._producer.start()
        return self._producer


class KafkaEventConsumer:
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        group_id: str,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._auto_offset_reset = auto_offset_reset
        self._consumer: AIOKafkaConsumer | None = None

    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        self._consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset=self._auto_offset_reset,
            enable_auto_commit=False,
        )
        await self._consumer.start()
        try:
            async for message in self._consumer:
                try:
                    event = EventEnvelope.from_json(message.value)
                    await handler(event)
                    await self._consumer.commit()
                except (TypeError, ValueError, KeyError):
                    logger.warning("Invalid Kafka event payload", exc_info=True)
                    await self._consumer.commit()
                except Exception:
                    logger.exception(
                        "Kafka event handling failed: topic=%s partition=%s offset=%s",
                        message.topic,
                        message.partition,
                        message.offset,
                    )
        finally:
            await self.stop()

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
