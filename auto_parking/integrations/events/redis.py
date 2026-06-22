import asyncio
import logging
from collections.abc import Sequence

from redis.asyncio import Redis
from redis.exceptions import RedisError

from auto_parking.ports.events import EventEnvelope, EventHandler

logger = logging.getLogger(__name__)


class RedisEventProducer:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def publish(
        self,
        topic: str,
        event: EventEnvelope,
        *,
        key: str | None = None,
    ) -> None:
        await self._redis.publish(topic, event.to_json())

    async def close(self) -> None:
        await self._redis.aclose()


class RedisEventConsumer:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._stopping = False

    async def subscribe(self, topics: Sequence[str], handler: EventHandler) -> None:
        pubsub = self._redis.pubsub()
        try:
            await pubsub.subscribe(*topics)
            async for message in pubsub.listen():
                if self._stopping:
                    return
                if message["type"] != "message":
                    continue
                try:
                    event = EventEnvelope.from_json(message["data"])
                except (TypeError, ValueError, KeyError):
                    logger.warning("Invalid Redis event payload", exc_info=True)
                    continue
                await handler(event)
        except asyncio.CancelledError:
            raise
        except RedisError:
            logger.warning("Redis event consumer failed", exc_info=True)
            await asyncio.sleep(1)
            if not self._stopping:
                await self.subscribe(topics, handler)
        finally:
            await pubsub.aclose()

    async def stop(self) -> None:
        self._stopping = True
        await self._redis.aclose()
