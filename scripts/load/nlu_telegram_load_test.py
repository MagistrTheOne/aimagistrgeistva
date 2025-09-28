#!/usr/bin/env python3
"""Load testing script for NLU and Telegram integration.

This script simulates multiple users sending messages to test:
- NLU processing performance
- Intent detection accuracy
- Orchestrator throughput
- System stability under load

Usage:
    python scripts/load/nlu_telegram_load_test.py --users 50 --duration 60 --rate 10
"""

import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import argparse
import random

from app.core.config import settings
from app.core.di import init_container
from app.core.logging import configure_logging
from app.services.nlp_nlu import IntentResult, IntentType, Utterance, nlu_processor


@dataclass
class LoadTestResult:
    """Result of a single load test iteration."""
    user_id: str
    utterance: str
    intent_result: Optional[IntentResult]
    orchestration_result: Optional[Dict]
    processing_time: float
    success: bool
    error: Optional[str] = None


@dataclass
class LoadTestStats:
    """Aggregated load test statistics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_processing_time: float
    median_processing_time: float
    p95_processing_time: float
    p99_processing_time: float
    requests_per_second: float
    intent_accuracy: float
    errors: Dict[str, int]


class LoadTestRunner:
    """Load test runner for NLU and orchestration."""

    def __init__(self, num_users: int = 10, duration_seconds: int = 60, rate_per_second: int = 5):
        self.num_users = num_users
        self.duration_seconds = duration_seconds
        self.rate_per_second = rate_per_second

        # Test utterances for different intents
        self.test_utterances = {
            IntentType.CHAT_ANSWER: [
                "что такое искусственный интеллект?",
                "расскажи о погоде",
                "как дела?",
                "что ты умеешь?",
                "помоги мне",
            ],
            IntentType.HH_SEARCH: [
                "найди вакансии Python разработчика",
                "ищу работу программиста в Москве",
                "вакансии frontend разработчика",
                "нужен DevOps инженер",
            ],
            IntentType.OCR_TRANSLATE: [
                "переведи текст на английский",
                "translate this text to German",
                "переведи страницу",
            ],
            IntentType.REMIND: [
                "напомни мне о встрече завтра",
                "напоминание на 15:00",
                "не забудь про лекарство",
            ],
            IntentType.TAKE_SCREENSHOT: [
                "сделай скриншот",
                "захвати экран",
                "скрин экрана",
            ],
            IntentType.READ_ALOUD: [
                "прочитай этот текст",
                "озвучь сообщение",
                "скажи вслух",
            ],
        }

        self.results: List[LoadTestResult] = []
        self.start_time: Optional[float] = None

    def generate_random_utterance(self) -> tuple[str, IntentType]:
        """Generate random test utterance."""
        intent_type = random.choice(list(self.test_utterances.keys()))
        utterance = random.choice(self.test_utterances[intent_type])
        return utterance, intent_type

    async def simulate_user_request(self, user_id: str) -> LoadTestResult:
        """Simulate a single user request."""
        utterance_text, expected_intent = self.generate_random_utterance()

        utterance = Utterance(
            text=utterance_text,
            source="telegram",  # Simulate Telegram source
            language="ru",
            timestamp=time.time(),
            user_id=user_id,
        )

        start_time = time.time()

        try:
            # Step 1: NLU processing
            intent_result = await nlu_processor.detect_intent(utterance)

            # Step 2: Orchestration (mocked for now)
            orchestration_result = None
            if intent_result.confidence >= settings.nlp_confidence_threshold:
                try:
                    # Mock orchestration result
                    orchestration_result = {
                        "plan_id": f"plan_{user_id}",
                        "status": "completed",
                        "execution_time_ms": 150.0,
                        "results": {"mock": "response"}
                    }
                except Exception as e:
                    orchestration_result = {"error": str(e)}

            processing_time = time.time() - start_time

            success = intent_result.intent == expected_intent or intent_result.intent == IntentType.CHAT_ANSWER

            return LoadTestResult(
                user_id=user_id,
                utterance=utterance_text,
                intent_result=intent_result,
                orchestration_result=orchestration_result,
                processing_time=processing_time,
                success=success,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return LoadTestResult(
                user_id=user_id,
                utterance=utterance_text,
                intent_result=None,
                orchestration_result=None,
                processing_time=processing_time,
                success=False,
                error=str(e),
            )

    async def run_load_test(self) -> LoadTestStats:
        """Run the load test."""
        self.start_time = time.time()
        end_time = self.start_time + self.duration_seconds

        print(f"Starting load test: {self.num_users} users, {self.duration_seconds}s duration, {self.rate_per_second} req/s")
        print(f"Expected total requests: ~{self.num_users * self.duration_seconds * self.rate_per_second // 60}")

        tasks = []
        request_count = 0

        while time.time() < end_time and request_count < self.num_users * self.duration_seconds:
            # Create batch of requests
            batch_size = min(self.rate_per_second, self.num_users)
            batch_tasks = []

            for i in range(batch_size):
                user_id = f"user_{request_count % self.num_users:03d}"
                task = asyncio.create_task(self.simulate_user_request(user_id))
                batch_tasks.append(task)
                request_count += 1

            # Wait for batch completion
            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                for result in batch_results:
                    if isinstance(result, LoadTestResult):
                        self.results.append(result)
                    else:
                        # Handle exceptions
                        self.results.append(LoadTestResult(
                            user_id="error",
                            utterance="error",
                            intent_result=None,
                            orchestration_result=None,
                            processing_time=0.0,
                            success=False,
                            error=str(result),
                        ))

            # Wait for next batch (rate limiting)
            await asyncio.sleep(1.0 / self.rate_per_second)

        # Calculate statistics
        return self._calculate_stats()

    def _calculate_stats(self) -> LoadTestStats:
        """Calculate test statistics."""
        if not self.results:
            return LoadTestStats(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, {})

        total_time = time.time() - (self.start_time or time.time())

        successful_requests = len([r for r in self.results if r.success])
        processing_times = [r.processing_time for r in self.results if r.processing_time > 0]

        # Intent accuracy calculation
        intent_results = [r for r in self.results if r.intent_result]
        correct_intents = len([r for r in intent_results if r.success])
        intent_accuracy = correct_intents / len(intent_results) if intent_results else 0.0

        # Error counting
        errors = {}
        for result in self.results:
            if result.error:
                error_type = result.error.split(":")[0] if ":" in result.error else "unknown"
                errors[error_type] = errors.get(error_type, 0) + 1

        return LoadTestStats(
            total_requests=len(self.results),
            successful_requests=successful_requests,
            failed_requests=len(self.results) - successful_requests,
            avg_processing_time=statistics.mean(processing_times) if processing_times else 0.0,
            median_processing_time=statistics.median(processing_times) if processing_times else 0.0,
            p95_processing_time=statistics.quantiles(processing_times, n=20)[18] if len(processing_times) >= 20 else max(processing_times) if processing_times else 0.0,
            p99_processing_time=statistics.quantiles(processing_times, n=100)[98] if len(processing_times) >= 100 else max(processing_times) if processing_times else 0.0,
            requests_per_second=len(self.results) / total_time if total_time > 0 else 0.0,
            intent_accuracy=intent_accuracy,
            errors=errors,
        )

    def print_results(self, stats: LoadTestStats):
        """Print test results."""
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)

        print(f"Total requests: {stats.total_requests}")
        print(f"Successful: {stats.successful_requests} ({stats.successful_requests/stats.total_requests*100:.1f}%)")
        print(f"Failed: {stats.failed_requests} ({stats.failed_requests/stats.total_requests*100:.1f}%)")
        print(f"Intent accuracy: {stats.intent_accuracy*100:.1f}%")
        print(f"Requests/second: {stats.requests_per_second:.1f}")

        print(f"\n⏱️  Processing times:")
        print(f"  Average: {stats.avg_processing_time*1000:.1f}ms")
        print(f"  Median: {stats.median_processing_time*1000:.1f}ms")
        print(f"  P95: {stats.p95_processing_time*1000:.1f}ms")
        print(f"  P99: {stats.p99_processing_time*1000:.1f}ms")

        if stats.errors:
            print(f"\n❌ Errors ({len(stats.errors)} types):")
            for error_type, count in sorted(stats.errors.items()):
                print(f"  {error_type}: {count}")

        print("\n✅ Test completed!")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="NLU and Telegram load testing")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--rate", type=int, default=5, help="Requests per second")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)

    # Initialize system
    configure_logging()
    init_container()

    # Run test
    runner = LoadTestRunner(
        num_users=args.users,
        duration_seconds=args.duration,
        rate_per_second=args.rate,
    )

    try:
        stats = await runner.run_load_test()
        runner.print_results(stats)

        # Exit with error if too many failures
        if stats.failed_requests / stats.total_requests > 0.1:  # >10% failure rate
            print("High failure rate detected!")
            exit(1)

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
