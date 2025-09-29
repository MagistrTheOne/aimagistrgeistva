"""Task management service with AI-powered parsing."""

import re
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from app.adapters.redis_client import redis_adapter
from app.core.logging import get_structlog_logger
from app.domain.models import Task, TaskCreateRequest, TaskUpdateRequest
from app.services.integrations.telegram import telegram_service
from app.services.llm.yandex_gpt import yandex_gpt
from app.services.voice.tts import tts

logger = get_structlog_logger(__name__)


class TaskService:
    """Service for managing tasks with AI parsing."""

    def __init__(self):
        self.redis = redis_adapter

    async def create_task(self, user_id: str, request: TaskCreateRequest) -> Task:
        """Create a new task with AI parsing if needed."""
        task_id = str(uuid4())

        # If description is not provided but title seems complex, use AI parsing
        description = request.description
        priority = request.priority
        due_date = request.due_date
        tags = request.tags or []

        if not description and len(request.title.split()) > 3:
            # Use AI to parse complex task descriptions
            parsed_task = await self._parse_task_with_ai(request.title)
            if parsed_task:
                description = parsed_task.get("description", description)
                priority = parsed_task.get("priority", priority)
                due_date = parsed_task.get("due_date", due_date)
                tags = parsed_task.get("tags", tags)

        # Create task object
        task = Task(
            id=uuid4(),
            user_id=user_id,
            title=request.title,
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags,
            status="pending"
        )

        # Store in Redis
        await self.redis.add_task(task_id, {
            "id": task_id,
            "user_id": user_id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "due_date": task.due_date,
            "tags": task.tags,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        })

        logger.info("Task created", task_id=task_id, user_id=user_id, title=task.title)
        return task

    async def get_user_tasks(self, user_id: str, status: Optional[str] = None, limit: int = 50) -> List[Task]:
        """Get user's tasks with optional filtering."""
        tasks_data = await self.redis.get_user_tasks(user_id)
        tasks = []

        for task_data in tasks_data[:limit]:
            task = Task(**task_data)
            if status is None or task.status == status:
                tasks.append(task)

        return tasks

    async def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        """Get a specific task by ID."""
        task_data = await self.redis.get_task(task_id)
        if not task_data or task_data.get("user_id") != user_id:
            return None

        return Task(**task_data)

    async def update_task(self, user_id: str, task_id: str, request: TaskUpdateRequest) -> Optional[Task]:
        """Update an existing task."""
        task_data = await self.redis.get_task(task_id)
        if not task_data or task_data.get("user_id") != user_id:
            return None

        # Update fields
        updates = {}
        if request.title is not None:
            updates["title"] = request.title
        if request.description is not None:
            updates["description"] = request.description
        if request.priority is not None:
            updates["priority"] = request.priority
        if request.due_date is not None:
            updates["due_date"] = request.due_date
        if request.tags is not None:
            updates["tags"] = request.tags
        if request.status is not None:
            updates["status"] = request.status

        updates["updated_at"] = datetime.utcnow().isoformat()

        # Merge with existing data
        task_data.update(updates)
        await self.redis.add_task(task_id, task_data)

        logger.info("Task updated", task_id=task_id, updates=updates)
        return Task(**task_data)

    async def delete_task(self, user_id: str, task_id: str) -> bool:
        """Delete a task."""
        task_data = await self.redis.get_task(task_id)
        if not task_data or task_data.get("user_id") != user_id:
            return False

        # Remove from Redis (this is a simplified implementation)
        # In a real system, we'd have proper deletion
        await self.redis.update_task_status(task_id, "deleted")

        logger.info("Task deleted", task_id=task_id, user_id=user_id)
        return True

    async def _parse_task_with_ai(self, task_text: str) -> Optional[dict]:
        """Use AI to parse complex task descriptions."""
        try:
            prompt = f"""
            Проанализируй эту задачу и извлеки структурированную информацию:

            Задача: "{task_text}"

            Верни JSON с полями:
            - description: подробное описание задачи
            - priority: число от 1 до 5 (1 - низкий, 5 - критический)
            - due_date: дата в формате ISO если указана (или null)
            - tags: массив строк с ключевыми словами

            Если информация не указана, используй разумные значения по умолчанию.
            """

            response = await yandex_gpt.chat(prompt, temperature=0.1)

            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                import json
                try:
                    parsed = json.loads(json_match.group())
                    logger.info("Task parsed with AI", task_text=task_text, parsed=parsed)
                    return parsed
                except json.JSONDecodeError:
                    logger.warning("Failed to parse AI response as JSON", response=response)

            return None

        except Exception as e:
            logger.error("Failed to parse task with AI", error=str(e), task_text=task_text)
            return None

    async def get_overdue_tasks(self, user_id: str) -> List[Task]:
        """Get overdue tasks for a user."""
        tasks = await self.get_user_tasks(user_id)
        now = datetime.utcnow()
        overdue = []

        for task in tasks:
            if task.due_date and task.status != "completed":
                try:
                    due_date = datetime.fromisoformat(task.due_date.replace('Z', '+00:00'))
                    if due_date < now:
                        overdue.append(task)
                except ValueError:
                    continue

        return overdue

    async def schedule_reminder(self, user_id: str, task_id: str, reminder_time: datetime) -> None:
        """Schedule a reminder notification for a task."""
        task = await self.get_task(user_id, task_id)
        if not task:
            return

        notification = {
            "type": "task_reminder",
            "title": f"Напоминание: {task.title}",
            "message": task.description or task.title,
            "task_id": task_id,
            "priority": "normal"
        }

        await self.redis.schedule_notification(user_id, notification, delay_seconds=0)

    async def send_voice_reminder(self, user_id: str, task: Task) -> None:
        """Send a voice reminder for a task via Telegram."""
        try:
            # Generate voice message
            reminder_text = f"Напоминаю о задаче: {task.title}"
            if task.description:
                reminder_text += f". {task.description}"

            if task.due_date:
                reminder_text += f". Срок выполнения: {task.due_date}"

            # Generate voice using TTS
            voice_data = await tts.synthesize(
                text=reminder_text,
                language="ru-RU",
                format="oggopus"
            )

            # Send voice message via Telegram
            # Note: We need to map user_id to chat_id
            # This is a simplified implementation
            chat_id = int(user_id) if user_id.isdigit() else None
            if chat_id:
                await telegram_service.send_voice(
                    chat_id=chat_id,
                    voice_data=voice_data,
                    reply_to_message_id=None
                )

                logger.info("Voice reminder sent", task_id=str(task.id), user_id=user_id)

        except Exception as e:
            logger.error("Failed to send voice reminder", error=str(e), task_id=str(task.id))

    async def process_due_reminders(self) -> None:
        """Process and send due reminders (to be called by cron job)."""
        # This method would be called periodically to check for due reminders
        # For now, it's a placeholder for the cron job implementation

        # Get all users with pending notifications
        # This is a simplified implementation - in production would scan all users
        logger.info("Processing due reminders (placeholder)")

        # In a real implementation, this would:
        # 1. Scan all users
        # 2. Get their due notifications
        # 3. Send voice/text reminders
        # 4. Update notification status


# Global task service instance
task_service = TaskService()
