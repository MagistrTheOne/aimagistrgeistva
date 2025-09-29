"""Redis client adapter."""

import asyncio
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

    # Task Management
    async def add_task(self, task_id: str, task_data: dict) -> None:
        """Add task to Redis."""
        key = f"task:{task_id}"
        await self.set_json(key, task_data)
        # Add to user's task list
        user_id = task_data.get("user_id")
        if user_id:
            await self._client.sadd(f"user_tasks:{user_id}", task_id)

    async def get_task(self, task_id: str) -> Optional[dict]:
        """Get task by ID."""
        key = f"task:{task_id}"
        return await self.get_json(key)

    async def get_user_tasks(self, user_id: str) -> list:
        """Get all tasks for user."""
        task_ids = await self._client.smembers(f"user_tasks:{user_id}")
        tasks = []
        for task_id in task_ids:
            task = await self.get_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    async def update_task_status(self, task_id: str, status: str) -> None:
        """Update task status."""
        task = await self.get_task(task_id)
        if task:
            task["status"] = status
            task["updated_at"] = str(asyncio.get_event_loop().time())
            await self.add_task(task_id, task)

    # Document Management
    async def store_document(self, doc_id: str, doc_data: dict) -> None:
        """Store document in Redis."""
        key = f"document:{doc_id}"
        await self.set_json(key, doc_data, ttl=86400 * 30)  # 30 days

    async def get_document(self, doc_id: str) -> Optional[dict]:
        """Get document by ID."""
        key = f"document:{doc_id}"
        return await self.get_json(key)

    # Financial Records
    async def add_expense(self, user_id: str, expense_data: dict) -> None:
        """Add expense record."""
        expense_id = f"expense_{user_id}_{int(asyncio.get_event_loop().time())}"
        key = f"expense:{expense_id}"
        expense_data["id"] = expense_id
        await self.set_json(key, expense_data)
        # Add to user's expenses
        await self._client.lpush(f"user_expenses:{user_id}", expense_id)

    async def get_user_expenses(self, user_id: str, limit: int = 50) -> list:
        """Get recent expenses for user."""
        expense_ids = await self._client.lrange(f"user_expenses:{user_id}", 0, limit - 1)
        expenses = []
        for expense_id in expense_ids:
            expense = await self.get_json(f"expense:{expense_id}")
            if expense:
                expenses.append(expense)
        return expenses

    # RSS Feed Cache
    async def cache_feed_item(self, feed_url: str, item_data: dict, ttl: int = 3600) -> None:
        """Cache RSS feed item."""
        item_id = item_data.get("guid", item_data.get("link", ""))
        if item_id:
            key = f"feed_item:{feed_url}:{item_id}"
            await self.set_json(key, item_data, ttl)

    async def get_cached_feed_items(self, feed_url: str) -> list:
        """Get cached feed items for URL."""
        pattern = f"feed_item:{feed_url}:*"
        keys = await self._client.keys(pattern)
        items = []
        for key in keys:
            item = await self.get_json(key)
            if item:
                items.append(item)
        return items

    # User Preferences
    async def set_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set user preference."""
        pref_key = f"user_pref:{user_id}:{key}"
        if isinstance(value, (dict, list)):
            await self.set_json(pref_key, value)
        else:
            await self.set(pref_key, str(value))

    async def get_user_preference(self, user_id: str, key: str) -> Any:
        """Get user preference."""
        pref_key = f"user_pref:{user_id}:{key}"
        return await self.get_json(pref_key) or await self.get(pref_key)

    # Background Jobs Queue
    async def enqueue_job(self, job_type: str, job_data: dict) -> None:
        """Add job to queue."""
        job_id = f"{job_type}_{int(asyncio.get_event_loop().time())}_{id(job_data)}"
        job = {
            "id": job_id,
            "type": job_type,
            "data": job_data,
            "created_at": str(asyncio.get_event_loop().time()),
            "status": "pending"
        }
        await self._client.lpush(f"queue:{job_type}", json.dumps(job))

    async def dequeue_job(self, job_type: str) -> Optional[dict]:
        """Get next job from queue."""
        job_data = await self._client.rpop(f"queue:{job_type}")
        if job_data:
            return json.loads(job_data)
        return None

    # Notification Queue
    async def schedule_notification(self, user_id: str, notification: dict, delay_seconds: int = 0) -> None:
        """Schedule notification for user."""
        if delay_seconds > 0:
            # Use Redis sorted set for delayed notifications
            score = asyncio.get_event_loop().time() + delay_seconds
            await self._client.zadd(f"notifications:{user_id}", {json.dumps(notification): score})
        else:
            # Immediate notification
            await self._client.lpush(f"notifications:{user_id}", json.dumps(notification))

    async def get_pending_notifications(self, user_id: str) -> list:
        """Get pending notifications for user."""
        notifications = await self._client.lrange(f"notifications:{user_id}", 0, -1)
        return [json.loads(n) for n in notifications]

    async def get_due_notifications(self, user_id: str) -> list:
        """Get notifications that are due now."""
        current_time = asyncio.get_event_loop().time()
        # Get notifications with score <= current_time
        due_items = await self._client.zrangebyscore(f"notifications:{user_id}", 0, current_time)
        if due_items:
            # Remove them from the set
            await self._client.zremrangebyscore(f"notifications:{user_id}", 0, current_time)
            return [json.loads(item) for item in due_items]
        return []

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected


# Global Redis instance
redis_adapter = RedisAdapter()
