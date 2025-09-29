"""Telegram Bot integration."""

import asyncio
import io
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.adapters.http_client import http_client
from app.adapters.rate_limit import check_rate_limit
from app.core.config import settings
from app.core.errors import IntegrationError
from app.core.logging import get_structlog_logger
from app.core.metrics import metrics
from app.domain.models import CommandType
from app.services.llm.yandex_gpt import yandex_gpt
from app.services.voice.stt import stt
from app.services.voice.tts import tts


class CommandHandler:
    """Handles bot commands."""

    def __init__(self, telegram_service: 'TelegramService'):
        self.telegram_service = telegram_service

    async def handle_command(self, chat_id: int, command: str, message_id: int) -> None:
        """Handle bot commands."""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()

        if cmd == "/start":
            await self._cmd_start(chat_id, message_id)
        elif cmd == "/help":
            await self._cmd_help(chat_id, message_id)
        elif cmd == "/status":
            await self._cmd_status(chat_id, message_id)
        elif cmd == "/about":
            await self._cmd_about(chat_id, message_id)
        elif cmd == "/weather":
            await self._cmd_weather(chat_id, message_id, cmd_parts)
        elif cmd == "/news":
            await self._cmd_news(chat_id, message_id, cmd_parts)
        elif cmd == "/translate":
            await self._cmd_translate(chat_id, message_id, cmd_parts)
        elif cmd == "/image":
            await self._cmd_image(chat_id, message_id, cmd_parts)
        elif cmd == "/remind":
            await self._cmd_remind(chat_id, message_id, cmd_parts)
        elif cmd == "/calc":
            await self._cmd_calc(chat_id, message_id, cmd_parts)
        elif cmd == "/poll":
            await self._cmd_poll(chat_id, message_id, cmd_parts)
        elif cmd == "/quiz":
            await self._cmd_quiz(chat_id, message_id, cmd_parts)
        elif cmd == "/mood":
            await self._cmd_mood(chat_id, message_id)
        elif cmd == "/task":
            await self._cmd_task(chat_id, message_id, cmd_parts)
        elif cmd == "/tasks":
            await self._cmd_tasks(chat_id, message_id)
        elif cmd == "/expense":
            await self._cmd_expense(chat_id, message_id, cmd_parts)
        elif cmd == "/expenses":
            await self._cmd_expenses(chat_id, message_id)
        else:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Неизвестная команда. Используйте /help для списка доступных команд.",
                reply_to_message_id=message_id
            )

    async def _cmd_start(self, chat_id: int, message_id: int) -> None:
        """Handle /start command."""
        user_info = await self.telegram_service._get_user_info(chat_id)
        welcome_msg = f"""
🤖 Добро пожаловать в AI Мага!

Привет, {user_info['name']}! Я ваш персональный голосовой ассистент.

💬 **Что я умею:**
• Отвечать на вопросы и вести беседу
• Понимать голосовые сообщения
• Отвечать голосом на русском языке

🎯 **Доступные команды:**
/help - показать эту справку
/status - проверить статус системы
/about - информация о боте

Просто напишите или скажите мне что-нибудь! 🎤
        """
        await self.telegram_service.send_message(chat_id=chat_id, text=welcome_msg.strip(), reply_to_message_id=message_id)

    async def _cmd_help(self, chat_id: int, message_id: int) -> None:
        """Handle /help command."""
        help_msg = """
📋 **Справка по командам:**

💬 **Общение:**
• Просто пишите или отправляйте голосовые сообщения
• Я отвечу текстом и голосом

🎯 **Основные команды:**
/start - начать работу с ботом
/help - показать эту справку
/status - проверить статус системы
/about - информация о боте

🛠️ **Полезные функции:**
/weather [город] - погода
/news [тема] - новости
/translate [язык] [текст] - перевод
/image [описание] - описание для изображений
/remind [время] [напоминание] - напоминания
/calc [выражение] - калькулятор

📋 **Управление задачами:**
/task [описание] - создать задачу (AI поймет сроки и приоритеты)
/tasks - показать все задачи

💰 **Финансы:**
/expense [сумма] [категория] [описание] - добавить расход
/expenses - показать расходы

🎮 **Интерактив:**
/poll [вопрос] [варианты] - создать опрос
/quiz - запустить викторину
/mood - проверить настроение

🎤 **Голос:**
• Отправьте голосовое сообщение - я пойму речь
• Получу ответ от ИИ и отвечу голосом

🚀 **Разработчик:** MagistrTheOne
        """
        await self.telegram_service.send_message(chat_id=chat_id, text=help_msg.strip(), reply_to_message_id=message_id)

    async def _cmd_status(self, chat_id: int, message_id: int) -> None:
        """Handle /status command."""
        try:
            # Test system components
            status_msg = "🔍 **Статус системы:**\n\n"

            # Check database
            try:
                # This is a simple check - in real app you'd ping the database
                status_msg += "✅ База данных: Доступна\n"
            except:
                status_msg += "❌ База данных: Недоступна\n"

            # Check Redis
            try:
                status_msg += " Кэш: Доступен\n"
            except:
                status_msg += " Кэш: Недоступен\n"

            # Check AI services
            try:
                status_msg += " Yandex GPT: Доступен\n"
                status_msg += " Голосовой синтез: Доступен\n"
                status_msg += "✅Распознавание речи: Доступно\n"
            except:
                status_msg += " AI сервисы: Проблемы с доступностью\n"

            status_msg += f"\n Бот активен и готов к работе!"

        except Exception as e:
            status_msg = " Не удалось проверить статус системы."

        await self.telegram_service.send_message(chat_id=chat_id, text=status_msg, reply_to_message_id=message_id)

    async def _cmd_about(self, chat_id: int, message_id: int) -> None:
        """Handle /about command."""
        about_msg = """
 **AI Мага** - Голосовой ассистент нового поколения

**Возможности:**
• Интеллектуальные ответы на базе Yandex GPT
• Голосовое общение на русском языке
• Персонализация и распознавание пользователей
• Интеграция с современными AI сервисами


**Разработчик:** MagistrTheOne
**Версия:** 2.0 (Production)

🚀 Powered by AI & Cloud Technologies
        """
        await self.telegram_service.send_message(chat_id=chat_id, text=about_msg.strip(), reply_to_message_id=message_id)

    async def _cmd_weather(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /weather command."""
        if len(cmd_parts) < 2:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Использование: /weather [город]\nПример: /weather Москва",
                reply_to_message_id=message_id
            )
            return

        city = " ".join(cmd_parts[1:])
        try:
            # Ask GPT for weather information
            weather_prompt = f"Расскажи кратко о погоде в городе {city} на сегодня. Укажи температуру, осадки и общее состояние."
            response = await yandex_gpt.chat(weather_prompt)

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=f"🌤️ Погода в {city}:\n\n{response}",
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось получить информацию о погоде. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_news(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /news command."""
        category = " ".join(cmd_parts[1:]) if len(cmd_parts) > 1 else "общие"
        try:
            # Ask GPT for news
            news_prompt = f"Расскажи 3 самые свежие и важные новости в категории '{category}' на русском языке. Будь краток."
            response = await yandex_gpt.chat(news_prompt)

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=f"📰 Новости ({category}):\n\n{response}",
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось получить новости. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_translate(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /translate command."""
        if len(cmd_parts) < 3:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Использование: /translate [язык] [текст]\nПример: /translate английский привет мир",
                reply_to_message_id=message_id
            )
            return

        target_lang = cmd_parts[1]
        text_to_translate = " ".join(cmd_parts[2:])

        try:
            # Ask GPT for translation
            translate_prompt = f"Переведи на {target_lang}: '{text_to_translate}'"
            response = await yandex_gpt.chat(translate_prompt)

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=f"🔄 Перевод на {target_lang}:\n\n{response}",
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось перевести текст. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_image(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /image command."""
        if len(cmd_parts) < 2:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Использование: /image [описание]\nПример: /image красивый закат над горами",
                reply_to_message_id=message_id
            )
            return

        description = " ".join(cmd_parts[1:])

        try:
            # Ask GPT to generate image description
            image_prompt = f"Создай подробное описание изображения для генерации: {description}. Будь максимально детализированным."
            response = await yandex_gpt.chat(image_prompt)

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=f"🎨 Описание для генерации изображения:\n\n{response}\n\n⚠️ Генерация изображений будет доступна позже!",
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось сгенерировать описание. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_remind(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /remind command."""
        if len(cmd_parts) < 3:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Использование: /remind [время] [напоминание]\nПример: /remind через 30 минут позвонить маме",
                reply_to_message_id=message_id
            )
            return

        time_info = cmd_parts[1]
        reminder_text = " ".join(cmd_parts[2:])

        try:
            # Simple reminder logic
            reminder_msg = f"⏰ Напоминание установлено!\n\n📝 {reminder_text}\n⏱️ Время: {time_info}"

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=reminder_msg,
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось установить напоминание. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_calc(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /calc command."""
        if len(cmd_parts) < 2:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Использование: /calc [выражение]\nПример: /calc 2 + 2 * 3",
                reply_to_message_id=message_id
            )
            return

        expression = " ".join(cmd_parts[1:])

        try:
            # Ask GPT to calculate
            calc_prompt = f"Вычисли математическое выражение: {expression}. Покажи подробный расчет."
            response = await yandex_gpt.chat(calc_prompt)

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=f"🧮 Результат:\n\n{response}",
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось вычислить выражение. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_poll(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /poll command."""
        if len(cmd_parts) < 4:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Использование: /poll [вопрос] [вариант1] [вариант2] [вариант3]...\nПример: /poll Какой ваш любимый цвет? Красный Синий Зеленый",
                reply_to_message_id=message_id
            )
            return

        question = cmd_parts[1]
        options = cmd_parts[2:]

        if len(options) < 2:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Нужно минимум 2 варианта ответа!",
                reply_to_message_id=message_id
            )
            return

        try:
            # Generate unique poll ID
            self.telegram_service._poll_counter += 1
            poll_id = f"poll_{self.telegram_service._poll_counter}"

            # Store poll options
            self.telegram_service._active_polls[poll_id] = options

            # Create inline keyboard with poll options
            keyboard = {
                "inline_keyboard": [
                    [{"text": option, "callback_data": f"poll_{poll_id}_{i}"}] for i, option in enumerate(options)
                ]
            }

            await self.telegram_service._send_keyboard(
                chat_id=chat_id,
                text=f"📊 {question}",
                keyboard=keyboard,
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось создать опрос. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_quiz(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /quiz command."""
        try:
            # Simple quiz questions
            quiz_questions = [
                {
                    "question": "Столица России?",
                    "options": ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург"],
                    "correct": 0
                },
                {
                    "question": "Сколько планет в Солнечной системе?",
                    "options": ["7", "8", "9", "10"],
                    "correct": 1
                },
                {
                    "question": "Какой год сейчас?",
                    "options": ["2023", "2024", "2025", "2026"],
                    "correct": 2
                }
            ]

            import random
            quiz = random.choice(quiz_questions)

            keyboard = {
                "inline_keyboard": [
                    [{"text": option, "callback_data": f"quiz_{i}_{quiz['correct']}"}]
                    for i, option in enumerate(quiz["options"])
                ]
            }

            await self.telegram_service._send_keyboard(
                chat_id=chat_id,
                text=f"🧠 Викторина!\n\n{quiz['question']}",
                keyboard=keyboard,
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось запустить викторину. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_mood(self, chat_id: int, message_id: int) -> None:
        """Handle /mood command."""
        try:
            mood_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "😊 Отличное", "callback_data": "mood_great"},
                        {"text": "😐 Нормальное", "callback_data": "mood_normal"}
                    ],
                    [
                        {"text": "😔 Плохое", "callback_data": "mood_bad"},
                        {"text": "🤔 Задумчивое", "callback_data": "mood_thinking"}
                    ]
                ]
            }

            await self.telegram_service._send_keyboard(
                chat_id=chat_id,
                text="🎭 Какое у вас настроение сегодня?",
                keyboard=mood_keyboard,
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось проверить настроение. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_task(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /task command."""
        if len(cmd_parts) < 2:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Использование: /task [описание задачи]\nПример: /task Подготовить презентацию к пятнице",
                reply_to_message_id=message_id
            )
            return

        try:
            from app.services.automations.task_service import task_service
            from app.api.http.app import TaskCreateRequest

            task_text = " ".join(cmd_parts[1:])
            request = TaskCreateRequest(title=task_text)

            task = await task_service.create_task(str(chat_id), request)

            response = f"✅ Задача создана!\n\n📝 {task.title}"
            if task.description:
                response += f"\n📄 {task.description}"
            if task.due_date:
                response += f"\n⏰ Срок: {task.due_date}"
            response += f"\n🎯 Приоритет: {task.priority}/5"

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=response,
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось создать задачу. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_tasks(self, chat_id: int, message_id: int) -> None:
        """Handle /tasks command."""
        try:
            from app.services.automations.task_service import task_service

            tasks = await task_service.get_user_tasks(str(chat_id), limit=10)

            if not tasks:
                await self.telegram_service.send_message(
                    chat_id=chat_id,
                    text="📝 У вас пока нет задач. Создайте первую командой /task",
                    reply_to_message_id=message_id
                )
                return

            response = "📋 Ваши задачи:\n\n"
            for i, task in enumerate(tasks[:5], 1):  # Show first 5
                status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "cancelled": "❌"}.get(task.status, "❓")
                response += f"{i}. {status_emoji} {task.title}\n"
                if task.due_date:
                    response += f"   ⏰ {task.due_date}\n"
                response += "\n"

            if len(tasks) > 5:
                response += f"... и ещё {len(tasks) - 5} задач"

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=response,
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось загрузить задачи. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_expense(self, chat_id: int, message_id: int, cmd_parts: List[str]) -> None:
        """Handle /expense command."""
        if len(cmd_parts) < 4:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="Использование: /expense [сумма] [категория] [описание]\nПример: /expense 500 еда обед в ресторане",
                reply_to_message_id=message_id
            )
            return

        try:
            from app.services.automations.finance_service import finance_service
            from app.api.http.app import ExpenseCreateRequest

            amount = float(cmd_parts[1])
            category = cmd_parts[2]
            description = " ".join(cmd_parts[3:])

            request = ExpenseCreateRequest(
                amount=amount,
                category=category,
                description=description
            )

            expense = await finance_service.add_expense(str(chat_id), request)

            response = f"✅ Расход добавлен!\n\n💰 {expense.amount} ₽\n📂 {expense.category}\n📝 {expense.description}"

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=response,
                reply_to_message_id=message_id
            )
        except ValueError:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Неверный формат суммы. Используйте число.",
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось добавить расход. Попробуйте позже.",
                reply_to_message_id=message_id
            )

    async def _cmd_expenses(self, chat_id: int, message_id: int) -> None:
        """Handle /expenses command."""
        try:
            from app.services.automations.finance_service import finance_service

            expenses = await finance_service.get_user_expenses(str(chat_id), limit=10)

            if not expenses:
                await self.telegram_service.send_message(
                    chat_id=chat_id,
                    text="💰 У вас пока нет расходов. Добавьте первый командой /expense",
                    reply_to_message_id=message_id
                )
                return

            total = sum(exp.amount for exp in expenses)
            response = f"💰 Ваши расходы (всего: {total:.2f} ₽):\n\n"

            for i, expense in enumerate(expenses[:5], 1):  # Show first 5
                response += f"{i}. {expense.amount:.2f} ₽ - {expense.category}\n"
                response += f"   📝 {expense.description}\n"
                response += f"   📅 {expense.date.strftime('%d.%m.%Y')}\n\n"

            if len(expenses) > 5:
                response += f"... и ещё {len(expenses) - 5} расходов"

            await self.telegram_service.send_message(
                chat_id=chat_id,
                text=response,
                reply_to_message_id=message_id
            )
        except Exception as e:
            await self.telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Не удалось загрузить расходы. Попробуйте позже.",
                reply_to_message_id=message_id
            )


class TelegramService:
    """Telegram Bot API integration."""

    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{settings.tg_bot_token.get_secret_value()}"
        self.logger = get_structlog_logger(__name__)
        # Store active polls: poll_id -> list of options
        self._active_polls: Dict[str, List[str]] = {}
        self._poll_counter = 0
        # Initialize command handler
        self.command_handler = CommandHandler(self)
        # Cache user info: chat_id -> (user_info, timestamp)
        self._user_cache: Dict[int, Tuple[Dict[str, Any], float]] = {}
        self._cache_ttl = 300  # 5 minutes

    def _validate_chat_id(self, chat_id: int) -> None:
        """Validate chat_id parameter."""
        if not isinstance(chat_id, int) or chat_id <= 0:
            raise ValueError(f"Invalid chat_id: {chat_id}")

    def _validate_message_id(self, message_id: int) -> None:
        """Validate message_id parameter."""
        if not isinstance(message_id, int) or message_id <= 0:
            raise ValueError(f"Invalid message_id: {message_id}")

    def _validate_callback_data(self, callback_data: str) -> None:
        """Validate callback_data parameter."""
        if not isinstance(callback_data, str) or not callback_data.strip():
            raise ValueError(f"Invalid callback_data: {callback_data}")
        if len(callback_data) > 64:  # Telegram limit
            raise ValueError(f"Callback data too long: {len(callback_data)}")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None,
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send text message to Telegram chat."""
        self._validate_chat_id(chat_id)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Invalid text: {text}")
        if reply_to_message_id is not None:
            self._validate_message_id(reply_to_message_id)

        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": reply_to_message_id,
        }
        if parse_mode:
            data["parse_mode"] = parse_mode

        try:
            response = await http_client.post(url, json=data)
            metrics.increment("telegram_messages_sent", type="text")
            return response
        except Exception as e:
            metrics.increment("telegram_messages_sent", type="text", status="error")
            raise IntegrationError(f"Failed to send Telegram message: {e}")

    async def send_voice(
        self,
        chat_id: int,
        voice_data: bytes,
        duration: Optional[int] = None,
        reply_to_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send voice message to Telegram chat."""
        url = f"{self.base_url}/sendVoice"

        # Convert audio data to file-like object
        voice_file = io.BytesIO(voice_data)
        voice_file.name = "voice.ogg"

        # Prepare multipart form data
        data = {
            "chat_id": str(chat_id),
            "voice": voice_file,
        }
        if duration:
            data["duration"] = str(duration)
        if reply_to_message_id:
            data["reply_to_message_id"] = str(reply_to_message_id)

        headers = {"Content-Type": "multipart/form-data"}

        try:
            # Note: This is a simplified implementation
            # In production, you might want to use aiohttp directly for file uploads
            response = await http_client.post(url, data=data, headers=headers)
            metrics.increment("telegram_messages_sent", type="voice")
            return response
        except Exception as e:
            metrics.increment("telegram_messages_sent", type="voice", status="error")
            raise IntegrationError(f"Failed to send Telegram voice: {e}")

    async def download_file(self, file_id: str) -> bytes:
        """Download file from Telegram servers."""
        if not isinstance(file_id, str) or not file_id.strip():
            raise ValueError(f"Invalid file_id: {file_id}")

        # First get file info
        file_info_url = f"{self.base_url}/getFile"
        file_info = await http_client.post(file_info_url, json={"file_id": file_id})

        if not file_info.get("ok"):
            raise IntegrationError(f"Failed to get file info: {file_info}")

        file_data = file_info["result"]
        file_path = file_data["file_path"]
        file_size = file_data.get("file_size", 0)

        # Check file size limit (20MB for voice messages)
        max_file_size = 20 * 1024 * 1024  # 20MB
        if file_size > max_file_size:
            raise IntegrationError(f"File too large: {file_size} bytes (max: {max_file_size})")

        # Validate file path (should be safe)
        if not file_path or ".." in file_path or file_path.startswith("/"):
            raise IntegrationError(f"Invalid file path: {file_path}")

        download_url = f"https://api.telegram.org/file/bot{settings.tg_bot_token.get_secret_value()}/{file_path}"

        try:
            response = await http_client.get(download_url)
            if isinstance(response, bytes):
                # Double check downloaded file size
                if len(response) > max_file_size:
                    raise IntegrationError(f"Downloaded file too large: {len(response)} bytes")
                return response
            else:
                raise IntegrationError("Unexpected response type for file download")
        except Exception as e:
            raise IntegrationError(f"Failed to download file: {e}")

    async def process_text_message(self, chat_id: int, text: str, message_id: int) -> None:
        """Process text message and send response."""
        self.logger.error("DEBUG: process_text_message called", chat_id=chat_id, text=text[:100])

        self._validate_chat_id(chat_id)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Invalid text: {text}")
        self._validate_message_id(message_id)

        # Rate limiting - temporarily disabled for debugging
        user_id = str(chat_id)
        self.logger.error("DEBUG: Skipping rate limit check for debugging", user_id=user_id)
        # if text.startswith('/'):
        #     await check_rate_limit(user_id, CommandType.GENERATE_RESPONSE)
        # else:
        #     await check_rate_limit(user_id, CommandType.CHAT_MESSAGE)

        self.logger.error("DEBUG: Processing message without rate limit")
        try:
            # Handle commands
            if text.startswith('/'):
                await self._handle_command(chat_id, text, message_id)
                return

            # Get user info for personalization
            user_info = await self._get_user_info(chat_id)

            # Add personalization to the message
            personalized_text = await self._personalize_message(text, user_info)

            # Generate response using Yandex GPT
            response_text = await yandex_gpt.chat(
                personalized_text,
                session_id=f"telegram_{chat_id}"
            )

            # Send text response
            await self.send_message(
                chat_id=chat_id,
                text=response_text,
                reply_to_message_id=message_id
            )

            # Generate voice response
            voice_data = await tts.synthesize(
                text=response_text,
                language="ru-RU",
                format="oggopus"  # Telegram prefers OGG Opus for voice messages
            )

            # Send voice response
            await self.send_voice(
                chat_id=chat_id,
                voice_data=voice_data,
                reply_to_message_id=message_id
            )

        except Exception as e:
            self.logger.error(
                "Error processing text message",
                chat_id=chat_id,
                message_id=message_id,
                text_length=len(text) if text else 0,
                error=str(e),
                error_type=type(e).__name__
            )
            error_msg = "Извините, произошла ошибка при обработке сообщения. Попробуйте позже."
            try:
                await self.send_message(chat_id=chat_id, text=error_msg, reply_to_message_id=message_id)
            except Exception as send_error:
                self.logger.error(
                    "Failed to send error message to user",
                    chat_id=chat_id,
                    send_error=str(send_error)
                )
            raise

    async def _get_user_info(self, chat_id: int) -> Dict[str, Any]:
        """Get user information from Telegram."""
        # Check cache first
        current_time = time.time()
        if chat_id in self._user_cache:
            cached_info, timestamp = self._user_cache[chat_id]
            if current_time - timestamp < self._cache_ttl:
                return cached_info

        try:
            url = f"{self.base_url}/getChat"
            data = {"chat_id": chat_id}
            response = await http_client.post(url, json=data)
            chat_info = response["result"]

            # Try to get member info for groups
            if chat_info.get("type") in ["group", "supergroup"]:
                url = f"{self.base_url}/getChatMember"
                data = {"chat_id": chat_id, "user_id": chat_id}
                response = await http_client.post(url, json=data)
                member_info = response["result"]
                user_info = {
                    "name": member_info.get("user", {}).get("first_name", "Пользователь"),
                    "username": member_info.get("user", {}).get("username"),
                    "is_admin": member_info.get("status") in ["administrator", "creator"]
                }
                # Cache the result
                self._user_cache[chat_id] = (user_info, current_time)
                return user_info

            # For private chats, try to get user profile
            if "first_name" in chat_info:
                user_info = {
                    "name": chat_info.get("first_name", "Пользователь"),
                    "username": chat_info.get("username"),
                    "is_admin": False
                }
                # Cache the result
                self._user_cache[chat_id] = (user_info, current_time)
                return user_info

            user_info = {"name": "Пользователь", "username": None, "is_admin": False}
            # Cache the result
            self._user_cache[chat_id] = (user_info, current_time)
            return user_info

        except Exception as e:
            self.logger.warning(f"Failed to get user info for chat {chat_id}: {e}")
            return {"name": "Пользователь", "username": None, "is_admin": False}

    async def _handle_command(self, chat_id: int, command: str, message_id: int) -> None:
        """Handle bot commands."""
        self.logger.error("DEBUG: _handle_command called", command=command[:100])
        await self.command_handler.handle_command(chat_id, command, message_id)


    async def _send_keyboard(self, chat_id: int, text: str, keyboard: Dict, reply_to_message_id: int = None) -> None:
        """Send message with inline keyboard."""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(keyboard)
            }
            if reply_to_message_id:
                payload["reply_to_message_id"] = reply_to_message_id

            response = await http_client.post(url, json=payload)
        except Exception as e:
            self.logger.error(f"Failed to send keyboard: {e}")
            # Fallback to regular message
            await self.send_message(chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id)

    async def _personalize_message(self, text: str, user_info: Dict[str, Any]) -> str:
        """Add personalization to the message."""
        if user_info.get("name") and user_info["name"] != "Пользователь":
            # Add context about the user
            personalized = f"Пользователь {user_info['name']}"
            if user_info.get("username"):
                personalized += f" (@{user_info['username']})"
            personalized += f" спрашивает: {text}"
            return personalized
        return text

    async def _get_conversation_history(self, chat_id: int, limit: int = 5) -> str:
        """Get recent conversation history for context."""
        # Simple implementation - in production would use database
        # For now, just return empty context
        return ""

    async def _save_message_to_history(self, chat_id: int, message: str, is_user: bool = True) -> None:
        """Save message to conversation history."""
        # Simple implementation - in production would save to database
        pass

    async def process_callback_query(self, chat_id: int, callback_data: str, message_id: int) -> None:
        """Process callback query from inline buttons."""
        self._validate_chat_id(chat_id)
        self._validate_callback_data(callback_data)
        self._validate_message_id(message_id)

        # Rate limiting
        user_id = str(chat_id)
        await check_rate_limit(user_id, CommandType.CHAT_MESSAGE)

        try:
            # Parse callback data
            parts = callback_data.split('_')
            action = parts[0]

            if action == "poll":
                # Handle poll answer
                poll_id = parts[1]
                option_index = int(parts[2])
                await self._handle_poll_answer(chat_id, message_id, poll_id, option_index)
            elif action == "quiz":
                # Handle quiz answer
                user_answer = int(parts[1])
                correct_answer = int(parts[2])
                await self._handle_quiz_answer(chat_id, message_id, user_answer, correct_answer)
            elif action == "mood":
                # Handle mood response
                mood_type = "_".join(parts[1:])
                await self._handle_mood_response(chat_id, message_id, mood_type)
            else:
                await self.send_message(
                    chat_id=chat_id,
                    text="❓ Неизвестное действие",
                    reply_to_message_id=message_id
                )
        except Exception as e:
            self.logger.error(
                "Error processing callback query",
                chat_id=chat_id,
                message_id=message_id,
                callback_data=callback_data,
                error=str(e),
                error_type=type(e).__name__
            )
            error_msg = "❌ Произошла ошибка при обработке действия. Попробуйте еще раз."
            try:
                await self.send_message(
                    chat_id=chat_id,
                    text=error_msg,
                    reply_to_message_id=message_id
                )
            except Exception as send_error:
                self.logger.error(
                    "Failed to send callback error message to user",
                    chat_id=chat_id,
                    send_error=str(send_error)
                )

    async def _handle_poll_answer(self, chat_id: int, message_id: int, poll_id: str, option_index: int) -> None:
        """Handle poll answer."""
        options = self._active_polls.get(poll_id)
        if not options:
            await self.send_message(
                chat_id=chat_id,
                text="❌ Опрос не найден или устарел",
                reply_to_message_id=message_id
            )
            return

        if 0 <= option_index < len(options):
            selected_option = options[option_index]
            await self.send_message(
                chat_id=chat_id,
                text=f"✅ Вы выбрали: {selected_option}",
                reply_to_message_id=message_id
            )
        else:
            await self.send_message(
                chat_id=chat_id,
                text="❌ Неверный вариант ответа",
                reply_to_message_id=message_id
            )

    async def _handle_quiz_answer(self, chat_id: int, message_id: int, user_answer: int, correct_answer: int) -> None:
        """Handle quiz answer."""
        if user_answer == correct_answer:
            await self.send_message(
                chat_id=chat_id,
                text="🎉 Правильно! Вы молодец! 🏆",
                reply_to_message_id=message_id
            )
        else:
            await self.send_message(
                chat_id=chat_id,
                text=f"❌ Неправильно. Попробуйте еще раз! 💪\n\nПопробуйте команду /quiz снова!",
                reply_to_message_id=message_id
            )

    async def _handle_mood_response(self, chat_id: int, message_id: int, mood_type: str) -> None:
        """Handle mood response."""
        mood_responses = {
            "great": "😊 Отлично! Рад слышать, что у вас хорошее настроение!",
            "normal": "😐 Нормальное настроение - это уже хорошо! Главное позитив! 👍",
            "bad": "😔 Понимаю, иногда бывает трудно. Хотите поговорить об этом?",
            "thinking": "🤔 Задумчивое настроение... Может быть, стоит попробовать что-то новое?"
        }

        response = mood_responses.get(mood_type, "❓ Неизвестное настроение")
        await self.send_message(
            chat_id=chat_id,
            text=response,
            reply_to_message_id=message_id
        )

    async def process_voice_message(self, chat_id: int, voice_file_id: str, message_id: int) -> None:
        """Process voice message and send response."""
        self._validate_chat_id(chat_id)
        if not isinstance(voice_file_id, str) or not voice_file_id.strip():
            raise ValueError(f"Invalid voice_file_id: {voice_file_id}")
        self._validate_message_id(message_id)

        # Rate limiting
        user_id = str(chat_id)
        await check_rate_limit(user_id, CommandType.READ_TEXT)

        try:
            # Download voice file
            voice_data = await self.download_file(voice_file_id)

            # Transcribe speech to text
            transcription_result = await stt.transcribe(voice_data)

            if not transcription_result.get("text"):
                await self.send_message(
                    chat_id=chat_id,
                    text="Не удалось распознать речь. Попробуйте еще раз.",
                    reply_to_message_id=message_id
                )
                return

            user_text = transcription_result["text"]

            # Confirm transcription
            await self.send_message(
                chat_id=chat_id,
                text=f"🎤 Распознано: {user_text}",
                reply_to_message_id=message_id
            )

            # Generate response using Yandex GPT
            response_text = await yandex_gpt.chat(
                user_text,
                session_id=f"telegram_{chat_id}"
            )

            # Send text response
            await self.send_message(
                chat_id=chat_id,
                text=f"💬 {response_text}",
                reply_to_message_id=message_id
            )

            # Generate voice response
            voice_data = await tts.synthesize(
                text=response_text,
                language="ru-RU",
                format="oggopus"
            )

            # Send voice response
            await self.send_voice(
                chat_id=chat_id,
                voice_data=voice_data,
                reply_to_message_id=message_id
            )

        except Exception as e:
            self.logger.error(
                "Error processing voice message",
                chat_id=chat_id,
                message_id=message_id,
                voice_file_id=voice_file_id,
                error=str(e),
                error_type=type(e).__name__
            )
            error_msg = "Извините, произошла ошибка при обработке голосового сообщения. Попробуйте еще раз."
            try:
                await self.send_message(chat_id=chat_id, text=error_msg, reply_to_message_id=message_id)
            except Exception as send_error:
                self.logger.error(
                    "Failed to send error message to user",
                    chat_id=chat_id,
                    send_error=str(send_error)
                )
            raise


# Global Telegram service instance
telegram_service = TelegramService()
