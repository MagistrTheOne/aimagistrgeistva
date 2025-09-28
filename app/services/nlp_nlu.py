"""Natural Language Understanding - интенты, слоты, confidence scoring."""

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Tuple

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.llm.yandex_gpt import yandex_gpt


class IntentType(str, Enum):
    """Типы интентов для AI Мага."""

    # Системные
    WAKE = "wake"
    SLEEP = "sleep"
    PAUSE = "pause"
    RESUME = "resume"
    SET_LANG = "set_lang"
    SET_VOLUME = "set_volume"

    # Коммуникация
    CHAT_ANSWER = "chat_answer"
    SUMMARIZE = "summarize"
    READ_ALOUD = "read_aloud"

    # Работа/поиск
    HH_SEARCH = "hh_search"
    JOBS_DIGEST = "jobs_digest"
    COMPOSE_REPLY = "compose_reply"

    # Визия/текст
    OCR_TRANSLATE = "ocr_translate"
    DESCRIBE_SCREEN = "describe_screen"

    # Рутина
    REMIND = "remind"
    SCHEDULE_TASK = "schedule_task"
    DAILY_DIGEST = "daily_digest"

    # Утилиты
    OPEN_APP = "open_app"
    TAKE_SCREENSHOT = "take_screenshot"
    CLIPBOARD_READ = "clipboard_read"


class SlotType(str, Enum):
    """Типы слотов для извлечения информации."""

    QUERY = "query"              # Поисковый запрос
    LANG = "lang"               # Язык (ru, en, etc.)
    WHEN = "when"               # Время/дата
    LOCATION = "location"       # Местоположение
    SENIORITY = "seniority"     # Опыт работы
    SALARY_MIN = "salary_min"   # Минимальная зарплата
    SALARY_MAX = "salary_max"   # Максимальная зарплата
    CHANNEL = "channel"         # Канал связи (telegram, email, etc.)
    DURATION = "duration"        # Продолжительность
    PRIORITY = "priority"       # Приоритет (1-5)


class IntentPattern(BaseModel):
    """Шаблон для распознавания интента."""

    intent: IntentType
    patterns: List[Pattern[str]]
    required_slots: List[SlotType] = Field(default_factory=list)
    optional_slots: List[SlotType] = Field(default_factory=list)
    confidence_boost: float = 0.0  # Дополнительный confidence для точных совпадений


class IntentResult(BaseModel):
    """Результат распознавания интента."""

    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    slots: Dict[SlotType, Any] = Field(default_factory=dict)
    raw_text: str
    explanation: Optional[str] = None


class Utterance(BaseModel):
    """Входное высказывание пользователя."""

    text: str
    source: str  # "voice", "telegram", "http"
    language: Optional[str] = None
    timestamp: float
    user_id: Optional[str] = None


class NLUProcessor:
    """Процессор естественного языка для распознавания интентов."""

    def __init__(self):
        self.intent_patterns = self._build_patterns()
        self.confidence_threshold = settings.nlp_confidence_threshold

    def _build_patterns(self) -> List[IntentPattern]:
        """Создать шаблоны для распознавания интентов."""

        patterns = []

        # Системные команды
        patterns.extend([
            IntentPattern(
                intent=IntentType.WAKE,
                patterns=[
                    re.compile(r'\b(мага|маша|алиса|слушай|проснись)\b', re.IGNORECASE),
                    re.compile(r'\b(wake|listen)\b', re.IGNORECASE),
                ],
                confidence_boost=0.3,
            ),
            IntentPattern(
                intent=IntentType.SLEEP,
                patterns=[
                    re.compile(r'\b(спать|усни|отдохни|пауза)\b', re.IGNORECASE),
                    re.compile(r'\b(sleep|rest|pause)\b', re.IGNORECASE),
                ],
                confidence_boost=0.2,
            ),
            IntentPattern(
                intent=IntentType.PAUSE,
                patterns=[
                    re.compile(r'\b(пауза|стоп|подожди|перерыв)\b', re.IGNORECASE),
                    re.compile(r'\b(pause|stop|wait)\b', re.IGNORECASE),
                ],
                confidence_boost=0.2,
            ),
        ])

        # Коммуникация
        patterns.extend([
            IntentPattern(
                intent=IntentType.CHAT_ANSWER,
                patterns=[
                    re.compile(r'\b(что|как|почему|зачем|расскажи)\b', re.IGNORECASE),
                    re.compile(r'\b(what|how|why|tell)\b', re.IGNORECASE),
                ],
                confidence_boost=0.1,
            ),
            IntentPattern(
                intent=IntentType.SUMMARIZE,
                patterns=[
                    re.compile(r'\b(суммируй|кратко|резюме|обзор)\b', re.IGNORECASE),
                    re.compile(r'\b(summarize|brief|overview)\b', re.IGNORECASE),
                ],
                confidence_boost=0.2,
            ),
            IntentPattern(
                intent=IntentType.READ_ALOUD,
                patterns=[
                    re.compile(r'\b(прочитай|озвучь|проговаривай)\b', re.IGNORECASE),
                    re.compile(r'\b(read|say|pronounce)\b', re.IGNORECASE),
                ],
                optional_slots=[SlotType.LANG],
                confidence_boost=0.2,
            ),
        ])

        # Работа/поиск
        patterns.extend([
            IntentPattern(
                intent=IntentType.HH_SEARCH,
                patterns=[
                    re.compile(r'\b(найди|ищи|поиск).*?(ваканси|работ|джоб|hh)\b', re.IGNORECASE),
                    re.compile(r'\b(find|search).*?(job|vacancy|work)\b', re.IGNORECASE),
                ],
                optional_slots=[SlotType.QUERY, SlotType.LOCATION, SlotType.SENIORITY, SlotType.SALARY_MIN, SlotType.SALARY_MAX],
                confidence_boost=0.3,
            ),
            IntentPattern(
                intent=IntentType.JOBS_DIGEST,
                patterns=[
                    re.compile(r'\b(дайджест|обзор|новости).*?(ваканси|работ|джоб)\b', re.IGNORECASE),
                    re.compile(r'\b(digest|overview|news).*?(job|vacancy)\b', re.IGNORECASE),
                ],
                confidence_boost=0.2,
            ),
            IntentPattern(
                intent=IntentType.COMPOSE_REPLY,
                patterns=[
                    re.compile(r'\b(напиши|составь|ответь).*?(сообщение|письмо|ответ)\b', re.IGNORECASE),
                    re.compile(r'\b(write|compose).*?(message|letter|reply)\b', re.IGNORECASE),
                ],
                optional_slots=[SlotType.QUERY, SlotType.CHANNEL],
                confidence_boost=0.2,
            ),
        ])

        # Визия/текст
        patterns.extend([
            IntentPattern(
                intent=IntentType.OCR_TRANSLATE,
                patterns=[
                    re.compile(r'\b(переведи|translate).*?(текст|экран|изображение)\b', re.IGNORECASE),
                    re.compile(r'\b(translate|переведи).*?(text|screen|image)\b', re.IGNORECASE),
                ],
                optional_slots=[SlotType.LANG],
                confidence_boost=0.3,
            ),
            IntentPattern(
                intent=IntentType.DESCRIBE_SCREEN,
                patterns=[
                    re.compile(r'\b(опиши|расскажи).*?(экран|изображение)\b', re.IGNORECASE),
                    re.compile(r'\b(describe|tell).*?(screen|image)\b', re.IGNORECASE),
                ],
                confidence_boost=0.2,
            ),
        ])

        # Рутина
        patterns.extend([
            IntentPattern(
                intent=IntentType.REMIND,
                patterns=[
                    re.compile(r'\b(напомни|напоминание|remind)\b', re.IGNORECASE),
                ],
                optional_slots=[SlotType.QUERY, SlotType.WHEN, SlotType.DURATION],
                confidence_boost=0.2,
            ),
            IntentPattern(
                intent=IntentType.SCHEDULE_TASK,
                patterns=[
                    re.compile(r'\b(запланируй|планировщик|schedule)\b', re.IGNORECASE),
                ],
                optional_slots=[SlotType.QUERY, SlotType.WHEN, SlotType.PRIORITY],
                confidence_boost=0.2,
            ),
            IntentPattern(
                intent=IntentType.DAILY_DIGEST,
                patterns=[
                    re.compile(r'\b(ежедневный|daily).*?(дайджест|обзор|digest)\b', re.IGNORECASE),
                ],
                confidence_boost=0.2,
            ),
        ])

        # Утилиты
        patterns.extend([
            IntentPattern(
                intent=IntentType.OPEN_APP,
                patterns=[
                    re.compile(r'\b(открой|запустить|open).*?(приложение|программа|app)\b', re.IGNORECASE),
                ],
                optional_slots=[SlotType.QUERY],
                confidence_boost=0.2,
            ),
            IntentPattern(
                intent=IntentType.TAKE_SCREENSHOT,
                patterns=[
                    re.compile(r'\b(скриншот|снимок|screenshot)\b', re.IGNORECASE),
                ],
                confidence_boost=0.3,
            ),
            IntentPattern(
                intent=IntentType.CLIPBOARD_READ,
                patterns=[
                    re.compile(r'\b(буфер|clipboard|вставь)\b', re.IGNORECASE),
                ],
                confidence_boost=0.2,
            ),
        ])

        return patterns

    def _extract_slots(self, text: str, intent: IntentType) -> Dict[SlotType, Any]:
        """Извлечь слоты из текста."""
        slots = {}

        # Извлечение языка
        lang_patterns = {
            SlotType.LANG: [
                (re.compile(r'\b(русский|russian|ru)\b', re.IGNORECASE), 'ru'),
                (re.compile(r'\b(английский|english|en)\b', re.IGNORECASE), 'en'),
                (re.compile(r'\b(немецкий|german|de)\b', re.IGNORECASE), 'de'),
                (re.compile(r'\b(французский|french|fr)\b', re.IGNORECASE), 'fr'),
            ]
        }

        for slot_type, patterns in lang_patterns.items():
            for pattern, value in patterns:
                if pattern.search(text):
                    slots[slot_type] = value
                    break

        # Извлечение локации
        location_match = re.search(r'\b(в|in)\s+(\w+)', text, re.IGNORECASE)
        if location_match:
            slots[SlotType.LOCATION] = location_match.group(2)

        # Извлечение зарплаты
        salary_match = re.search(r'\b(\d{4,6})\s*(руб|rub|rur|k|тыс|тысяч)', text, re.IGNORECASE)
        if salary_match:
            salary = int(salary_match.group(1))
            if 'тыс' in salary_match.group(2).lower() or 'k' in salary_match.group(2).lower():
                salary *= 1000
            slots[SlotType.SALARY_MIN] = salary

        # Извлечение опыта работы
        seniority_patterns = {
            SlotType.SENIORITY: [
                (re.compile(r'\b(джун|junior|младший)\b', re.IGNORECASE), 'junior'),
                (re.compile(r'\b(миддл|middle|средний)\b', re.IGNORECASE), 'middle'),
                (re.compile(r'\b(сеньор|senior|старший)\b', re.IGNORECASE), 'senior'),
                (re.compile(r'\b(тимлид|team.*lead|lead)\b', re.IGNORECASE), 'lead'),
            ]
        }

        for slot_type, patterns in seniority_patterns.items():
            for pattern, value in patterns:
                if pattern.search(text):
                    slots[slot_type] = value
                    break

        # Извлечение поискового запроса (для вакансий)
        if intent == IntentType.HH_SEARCH:
            # Ищем слова после "найди", "ищи", "поиск" до предлогов или цифр
            query_match = re.search(r'\b(найди|ищи|поиск)\s+(.+?)(?:\s+(?:в|на|от|до|с|\d+)|$)', text, re.IGNORECASE)
            if query_match:
                query = query_match.group(2).strip()
                # Убираем стоп-слова
                query = re.sub(r'\b(ваканси|работ|джоб|работу|вакансию)\b', '', query, flags=re.IGNORECASE).strip()
                if query:
                    slots[SlotType.QUERY] = query

        # Извлечение запроса для напоминаний
        if intent in [IntentType.REMIND, IntentType.SCHEDULE_TASK]:
            remind_match = re.search(r'\b(напомни|запланируй)\s+(.+?)(?:\s+(?:завтра|сегодня|через|в|на|\d+)|$)', text, re.IGNORECASE)
            if remind_match:
                slots[SlotType.QUERY] = remind_match.group(2).strip()

        return slots

    def _calculate_rule_based_confidence(
        self, text: str, pattern: IntentPattern
    ) -> Tuple[float, Dict[SlotType, Any]]:
        """Расчет confidence на основе правил."""
        max_confidence = 0.0
        best_match = None

        for regex_pattern in pattern.patterns:
            match = regex_pattern.search(text)
            if match:
                # Базовый confidence от длины совпадения
                match_length = len(match.group(0))
                text_length = len(text)
                base_confidence = min(match_length / text_length * 2.0, 0.8)

                # Увеличение за ключевые слова
                keyword_boost = 0.1 if len(pattern.patterns) == 1 else 0.05

                confidence = min(base_confidence + keyword_boost + pattern.confidence_boost, 0.95)

                if confidence > max_confidence:
                    max_confidence = confidence
                    best_match = match

        if max_confidence > 0:
            slots = self._extract_slots(text, pattern.intent)
            return max_confidence, slots

        return 0.0, {}

    async def _calculate_llm_confidence(
        self, text: str, rule_based_results: List[Tuple[IntentType, float, Dict[SlotType, Any]]]
    ) -> Optional[IntentResult]:
        """Расчет confidence с помощью LLM для уточнения."""

        if not rule_based_results:
            return None

        # Берем топ-3 кандидатов
        top_candidates = sorted(rule_based_results, key=lambda x: x[1], reverse=True)[:3]

        intents_str = ", ".join([f"{intent.value} ({conf:.2f})" for intent, conf, _ in top_candidates])

        prompt = f"""
Ты - AI Мага, эксперт по распознаванию намерений пользователя.

Проанализируй текст пользователя и выбери наиболее подходящее намерение из списка кандидатов.

Текст пользователя: "{text}"

Кандидаты (intent, confidence):
{intents_str}

Верни JSON в формате:
{{
  "intent": "chosen_intent",
  "confidence": 0.XX,
  "explanation": "краткое объяснение выбора"
}}

Если ни один кандидат не подходит (>0.3 confidence), верни fallback "chat_answer".
"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await yandex_gpt.generate(
                messages,
                temperature=0.1,
                max_tokens=150,
            )

            # Парсим JSON из ответа
            import json
            response_text = response["text"].strip()

            # Ищем JSON в ответе
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                llm_result = json.loads(json_str)

                intent_str = llm_result.get("intent", "chat_answer")
                confidence = llm_result.get("confidence", 0.5)

                # Преобразуем строку в IntentType
                try:
                    intent = IntentType(intent_str)
                except ValueError:
                    intent = IntentType.CHAT_ANSWER

                return IntentResult(
                    intent=intent,
                    confidence=min(confidence, 1.0),
                    raw_text=text,
                    explanation=llm_result.get("explanation"),
                )

        except Exception as e:
            print(f"LLM confidence calculation failed: {e}")

        return None

    async def detect_intent(self, utterance: Utterance) -> IntentResult:
        """Распознать интент в высказывании."""

        text = utterance.text.lower().strip()

        # Rule-based detection
        rule_results = []
        for pattern in self.intent_patterns:
            confidence, slots = self._calculate_rule_based_confidence(text, pattern)
            if confidence > 0:
                rule_results.append((pattern.intent, confidence, slots))

        # Если есть хорошие rule-based результаты
        if rule_results:
            best_intent, best_confidence, best_slots = max(rule_results, key=lambda x: x[1])

            # Если confidence достаточно высокий, возвращаем результат
            if best_confidence >= self.confidence_threshold:
                return IntentResult(
                    intent=best_intent,
                    confidence=best_confidence,
                    slots=best_slots,
                    raw_text=utterance.text,
                    explanation="rule-based",
                )

            # Иначе используем LLM для уточнения
            llm_result = await self._calculate_llm_confidence(text, rule_results)
            if llm_result and llm_result.confidence >= self.confidence_threshold:
                return llm_result

        # Fallback to chat_answer
        return IntentResult(
            intent=IntentType.CHAT_ANSWER,
            confidence=0.5,
            slots={SlotType.QUERY: utterance.text},
            raw_text=utterance.text,
            explanation="fallback",
        )


# Global NLU processor instance
nlu_processor = NLUProcessor()
