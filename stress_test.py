#!/usr/bin/env python3
"""
Stress test script for AI Мага API
Tests various endpoints under load
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, List
import statistics

BASE_URL = "http://localhost:8000"

class StressTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> Dict:
        """Make HTTP request and measure response time"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as resp:
                    response_time = time.time() - start_time
                    return {
                        "status": resp.status,
                        "response_time": response_time,
                        "success": resp.status < 400
                    }
            else:
                async with self.session.post(url, json=data, headers=headers) as resp:
                    response_time = time.time() - start_time
                    return {
                        "status": resp.status,
                        "response_time": response_time,
                        "success": resp.status < 400
                    }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "status": 0,
                "response_time": response_time,
                "success": False,
                "error": str(e)
            }

    async def test_health_check(self, iterations: int = 100) -> Dict:
        """Test health check endpoint"""
        print(f"[+] Testing health check ({iterations} iterations)...")
        results = []

        for i in range(iterations):
            result = await self.make_request("GET", "/healthz")
            results.append(result)

        return self._analyze_results("Health Check", results)

    async def test_chat_api(self, iterations: int = 50) -> Dict:
        """Test chat API with different messages"""
        print(f"[+] Testing chat API ({iterations} iterations)...")
        messages = [
            "Привет, как дела?",
            "Расскажи о себе",
            "Что ты умеешь делать?",
            "Помоги найти работу",
            "Переведи текст на английский: Привет мир",
            "Hello world",
            "Tell me about yourself",
            "What can you do?",
            "Help me find a job",
            "Translate: Hello world to Russian"
        ]

        results = []
        for i in range(iterations):
            msg = messages[i % len(messages)]
            data = {"text": msg, "session_id": f"stress_test_{i}"}
            result = await self.make_request("POST", "/v1/chat", data)
            results.append(result)

        return self._analyze_results("Chat API", results)

    async def test_intent_detection(self, iterations: int = 30) -> Dict:
        """Test intent detection"""
        print(f"[+] Testing intent detection ({iterations} iterations)...")
        test_texts = [
            "Найди работу Python разработчика",
            "Переведи текст на английский",
            "Создай напоминание на завтра",
            "Поиск вакансий в Москве",
            "Translate this text",
            "Remind me about meeting",
            "Find jobs in Moscow",
            "Расскажи новости",
            "Hello",
            "Goodbye"
        ]

        results = []
        for i in range(iterations):
            text = test_texts[i % len(test_texts)]
            data = {"text": text, "source": "api"}
            result = await self.make_request("POST", "/v1/intent/detect", data)
            results.append(result)

        return self._analyze_results("Intent Detection", results)

    async def test_system_status(self, iterations: int = 20) -> Dict:
        """Test system status endpoint"""
        print(f"[+] Testing system status ({iterations} iterations)...")
        results = []

        for i in range(iterations):
            result = await self.make_request("GET", "/v1/status")
            results.append(result)

        return self._analyze_results("System Status", results)

    async def test_voice_controls(self) -> Dict:
        """Test voice control endpoints"""
        print("[+] Testing voice controls...")
        results = []

        # Test enable
        result = await self.make_request("POST", "/v1/voice/enable")
        results.append(result)

        # Test disable
        result = await self.make_request("POST", "/v1/voice/disable")
        results.append(result)

        return self._analyze_results("Voice Controls", results)

    async def test_unimplemented_endpoints(self) -> Dict:
        """Test endpoints that return placeholders"""
        print("[+] Testing unimplemented endpoints...")
        results = []

        # Test HH.ru search
        data = {"query": "python developer", "location": "Moscow"}
        result = await self.make_request("GET", "/v1/jobs/hh/search", data)
        results.append(result)

        # Test OCR
        data = {"image_data": "test"}
        result = await self.make_request("POST", "/v1/vision/ocr", data)
        results.append(result)

        # Test translation
        data = {"text": "Hello world", "target_lang": "ru"}
        result = await self.make_request("POST", "/v1/translate", data)
        results.append(result)

        return self._analyze_results("Unimplemented Endpoints", results)

    def _analyze_results(self, test_name: str, results: List[Dict]) -> Dict:
        """Analyze test results"""
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        response_times = [r["response_time"] for r in results]

        analysis = {
            "test_name": test_name,
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else max(response_times)
        }

        if failed:
            analysis["failure_reasons"] = [r.get("error", f"HTTP {r['status']}") for r in failed[:5]]

        return analysis

    def print_report(self, results: List[Dict]):
        """Print test report"""
        print("\n" + "="*80)
        print("STRESS TEST AI MAGA - REPORT")
        print("="*80)

        for result in results:
            print(f"\n[*] {result['test_name']}")
            print(f"   Requests: {result['total_requests']}")
            print(f"   Success: {result['successful']}/{result['total_requests']} ({result['success_rate']:.1f}%)")
            print(f"   Avg time: {result['avg_response_time']:.3f} sec")
            print(f"   Min time: {result['min_response_time']:.3f} sec")
            print(f"   Max time: {result['max_response_time']:.3f} sec")
            print(f"   95th percentile: {result['p95_response_time']:.3f} sec")

            if result.get("failure_reasons"):
                print(f"   Errors: {result['failure_reasons']}")

async def main():
    """Run stress tests"""
    print("Starting AI Maga stress testing...")

    async with StressTester() as tester:
        results = []

        # Basic health checks
        results.append(await tester.test_health_check(100))
        results.append(await tester.test_system_status(20))

        # Core functionality
        results.append(await tester.test_chat_api(50))
        results.append(await tester.test_intent_detection(30))

        # Additional features
        results.append(await tester.test_voice_controls())
        results.append(await tester.test_unimplemented_endpoints())

        # Print final report
        tester.print_report(results)

        # Summary
        total_success_rate = sum(r["success_rate"] for r in results) / len(results)
        print(".1f")
        if total_success_rate >= 95:
            print("[+] System passed stress test! Everything works perfectly.")
        elif total_success_rate >= 80:
            print("[!] System works but has some issues with certain functions.")
        else:
            print("[-] System needs improvement.")

if __name__ == "__main__":
    asyncio.run(main())
