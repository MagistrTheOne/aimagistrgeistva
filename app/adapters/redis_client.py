"""Redis client adapter."""

import json
from typing import Any, Optional, Union

import redis.asyncio as redis

from app.core.config import settings
from app.core.di import RedisProtocol
from app.core.errors import RedisError


class RedisAdapter(RedisProtocol):
    """Redis client adapter."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._client = redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

            # Test connection
            await self._client.ping()
            self._connected = True

        except Exception as e:
            raise RedisError(f"Failed to connect to Redis: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._connected = False

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self._client:
            raise RedisError("Redis not connected")

        try:
            return await self._client.get(key)
        except Exception as e:
            raise RedisError(f"Redis GET failed: {e}")

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set key-value pair with optional TTL."""
        if not self._client:
            raise RedisError("Redis not connected")

        try:
            await self._client.set(key, value, ex=ttl)
        except Exception as e:
            raise RedisError(f"Redis SET failed: {e}")

    async def delete(self, key: str) -> int:
        """Delete key."""
        if not self._client:
            raise RedisError("Redis not connected")

        try:
            return await self._client.delete(key)
        except Exception as e:
            raise RedisError(f"Redis DELETE failed: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._client:
            raise RedisError("Redis not connected")

        try:
            return bool(await self._client.exists(key))
        except Exception as e:
            raise RedisError(f"Redis EXISTS failed: {e}")

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key."""
        if not self._client:
            raise RedisError("Redis not connected")

        try:
            return bool(await self._client.expire(key, ttl))
        except Exception as e:
            raise RedisError(f"Redis EXPIRE failed: {e}")

    async def incr(self, key: str) -> int:
        """Increment integer value."""
        if not self._client:
            raise RedisError("Redis not connected")

        try:
            return await self._client.incr(key)
        except Exception as e:
            raise RedisError(f"Redis INCR failed: {e}")

    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        if not self._client:
            raise RedisError("Redis not connected")

        try:
            return await self._client.publish(channel, message)
        except Exception as e:
            raise RedisError(f"Redis PUBLISH failed: {e}")

    async def set_json(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Set JSON data."""
        json_str = json.dumps(data, ensure_ascii=False)
        await self.set(key, json_str, ttl)

    async def get_json(self, key: str) -> Any:
        """Get JSON data."""
        value = await self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise RedisError(f"Invalid JSON in Redis: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected


# Global Redis instance
redis_adapter = RedisAdapter()
