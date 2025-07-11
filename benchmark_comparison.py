#!/usr/bin/env python3
"""
Backend Performance Comparison
Simple benchmark script to compare Old Backend vs New Backend performance
with clear line chart visualizations.
"""

import asyncio
import aiohttp
import time
import json
import statistics
import random
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================

# Backend URLs
OLD_BACKEND_URL = "http://localhost:5000"
NEW_BACKEND_URL = "http://localhost:8000"

# Test Configuration
USER_COUNTS = [1, 5, 10, 20, 50]  # Different concurrent user levels
REQUESTS_PER_USER = 10  # Requests each user makes
WARMUP_REQUESTS = 3  # Warmup requests

# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class TestResult:
    backend: str
    users: int
    avg_response_time: float
    p95_response_time: float
    throughput_rps: float
    error_rate: float
    total_requests: int
    successful_requests: int


# =============================================================================
# TEST DATA GENERATOR
# =============================================================================


class TestDataGenerator:
    """Generates realistic test data"""

    QUESTIONS = [
        "What is the company's vacation policy?",
        "How do I report sick leave?",
        "What are the benefits available?",
        "How do I access my pay stub?",
        "What is the remote work policy?",
        "How do I request time off?",
        "What are the office hours?",
        "How do I contact HR?",
        "What is the dress code policy?",
        "How do I submit an expense report?",
    ]

    RESPONSES = [
        "Based on company policy, employees receive 15 days of paid vacation annually.",
        "To report sick leave, please contact your manager and HR department.",
        "The company offers comprehensive health, dental, and vision insurance.",
        "You can access your pay stub through the employee portal.",
        "Remote work is allowed up to 3 days per week with manager approval.",
    ]

    @classmethod
    def generate_chat_request(cls) -> Dict[str, Any]:
        """Generate chat request"""
        return {
            "messages": [{"role": "user", "content": random.choice(cls.QUESTIONS)}],
            "stream": False,
            "context": {
                "overrides": {
                    "semantic_ranker": True,
                    "top": 3,
                    "suggest_followup_questions": False,
                }
            },
        }

    @classmethod
    def generate_vote_request(cls) -> Dict[str, Any]:
        """Generate vote request"""
        return {
            "user_query": random.choice(cls.QUESTIONS),
            "chatbot_response": random.choice(cls.RESPONSES),
            "upvote": random.choice([0, 1]),
            "downvote": random.choice([0, 1]),
            "email_address": f"user{random.randint(1, 100)}@company.com",
        }


# =============================================================================
# BENCHMARK ENGINE
# =============================================================================


class BenchmarkEngine:
    """Simple benchmark engine"""

    def __init__(self):
        self.results = []
        self.raw_data = []

    async def make_request(
        self, session, backend_url: str, endpoint: str, payload: Dict
    ) -> Dict:
        """Make a single request and return timing info"""
        start_time = time.time()
        success = False
        status_code = 0

        try:
            async with session.post(
                f"{backend_url}/{endpoint}", json=payload
            ) as response:
                status_code = response.status
                await response.text()  # Consume response
                success = 200 <= status_code < 300

        except Exception as e:
            success = False

        response_time = time.time() - start_time
        return {
            "response_time": response_time,
            "success": success,
            "status_code": status_code,
        }

    async def run_user_simulation(
        self, session, backend_url: str, users: int
    ) -> List[Dict]:
        """Simulate multiple users making requests"""
        results = []

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(users)

        async def single_user_requests():
            async with semaphore:
                user_results = []

                # Each user makes multiple requests
                for _ in range(REQUESTS_PER_USER):
                    # Mix of chat and vote requests
                    if random.choice([True, False]):
                        payload = TestDataGenerator.generate_chat_request()
                        endpoint = "chat"
                    else:
                        payload = TestDataGenerator.generate_vote_request()
                        endpoint = "vote"

                    result = await self.make_request(
                        session, backend_url, endpoint, payload
                    )
                    user_results.append(result)

                    # Small delay between requests
                    await asyncio.sleep(0.1)

                return user_results

        # Run all users concurrently
        user_tasks = [single_user_requests() for _ in range(users)]
        user_results = await asyncio.gather(*user_tasks)

        # Flatten results
        for user_result in user_results:
            results.extend(user_result)

        return results

    async def test_backend(
        self, backend_url: str, backend_name: str
    ) -> List[TestResult]:
        """Test a backend with different user counts"""
        results = []

        print(f"\n Testing {backend_name} backend...")

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:

            # Warmup
            print(f"  Warming up...")
            await self.run_user_simulation(session, backend_url, 1)

            # Test with different user counts
            for users in USER_COUNTS:
                print(f"  Testing with {users} concurrent users...")

                start_time = time.time()
                raw_results = await self.run_user_simulation(
                    session, backend_url, users
                )
                duration = time.time() - start_time

                # Calculate statistics
                response_times = [r["response_time"] for r in raw_results]
                successful = [r for r in raw_results if r["success"]]

                if response_times:
                    avg_response_time = statistics.mean(response_times)
                    p95_response_time = np.percentile(response_times, 95)
                    throughput_rps = len(successful) / duration
                    error_rate = (
                        (len(raw_results) - len(successful)) / len(raw_results) * 100
                    )

                    result = TestResult(
                        backend=backend_name,
                        users=users,
                        avg_response_time=avg_response_time,
                        p95_response_time=p95_response_time,
                        throughput_rps=throughput_rps,
                        error_rate=error_rate,
                        total_requests=len(raw_results),
                        successful_requests=len(successful),
                    )

                    results.append(result)

                    print(f"    Avg Response Time: {avg_response_time:.3f}s")
                    print(f"    Throughput: {throughput_rps:.1f} req/s")
                    print(f"    Error Rate: {error_rate:.1f}%")

                # Small delay between tests
                await asyncio.sleep(2)

        return results

    async def run_benchmark(self) -> List[TestResult]:
        """Run complete benchmark"""
        print("=== Backend Performance Comparison ===")
        print(f"Testing with user counts: {USER_COUNTS}")
        print(f"Requests per user: {REQUESTS_PER_USER}")

        all_results = []

        # Test Old Backend
        try:
            old_results = await self.test_backend(OLD_BACKEND_URL, "Old")
            all_results.extend(old_results)
        except Exception as e:
            print(f"Error testing old backend: {e}")

        # Test New Backend
        try:
            new_results = await self.test_backend(NEW_BACKEND_URL, "New")
            all_results.extend(new_results)
        except Exception as e:
            print(f"Error testing new backend: {e}")

        self.results = all_results
        return all_results


# =============================================================================
# VISUALIZATION
# =============================================================================


class BenchmarkVisualizer:
    """Create line charts comparing backends"""

    def __init__(self, results: List[TestResult]):
        self.results = results
        self.df = pd.DataFrame([vars(r) for r in results])

    def create_comparison_charts(self):
        """Create all comparison charts"""
        print("\n Creating comparison charts...")

        # Set up the plotting style
        plt.style.use("seaborn-v0_8")
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle("Backend Performance Comparison", fontsize=16, fontweight="bold")

        # 1. Average Response Time
        self._plot_response_time(axes[0, 0])

        # 2. Throughput (Requests per Second)
        self._plot_throughput(axes[0, 1])

        # 3. P95 Response Time
        self._plot_p95_response_time(axes[1, 0])

        # 4. Error Rate
        self._plot_error_rate(axes[1, 1])

        plt.tight_layout()

        # Save the chart
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backend_comparison_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"  Chart saved as: {filename}")

        plt.show()

    def _plot_response_time(self, ax):
        """Plot average response time comparison"""
        for backend in self.df["backend"].unique():
            data = self.df[self.df["backend"] == backend]
            ax.plot(
                data["users"],
                data["avg_response_time"],
                marker="o",
                linewidth=2,
                label=f"{backend} Backend",
            )

        ax.set_xlabel("Concurrent Users")
        ax.set_ylabel("Average Response Time (seconds)")
        ax.set_title("Average Response Time vs Concurrent Users")
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_throughput(self, ax):
        """Plot throughput comparison"""
        for backend in self.df["backend"].unique():
            data = self.df[self.df["backend"] == backend]
            ax.plot(
                data["users"],
                data["throughput_rps"],
                marker="s",
                linewidth=2,
                label=f"{backend} Backend",
            )

        ax.set_xlabel("Concurrent Users")
        ax.set_ylabel("Throughput (requests/second)")
        ax.set_title("Throughput vs Concurrent Users")
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_p95_response_time(self, ax):
        """Plot P95 response time comparison"""
        for backend in self.df["backend"].unique():
            data = self.df[self.df["backend"] == backend]
            ax.plot(
                data["users"],
                data["p95_response_time"],
                marker="^",
                linewidth=2,
                label=f"{backend} Backend",
            )

        ax.set_xlabel("Concurrent Users")
        ax.set_ylabel("P95 Response Time (seconds)")
        ax.set_title("P95 Response Time vs Concurrent Users")
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_error_rate(self, ax):
        """Plot error rate comparison"""
        for backend in self.df["backend"].unique():
            data = self.df[self.df["backend"] == backend]
            ax.plot(
                data["users"],
                data["error_rate"],
                marker="D",
                linewidth=2,
                label=f"{backend} Backend",
            )

        ax.set_xlabel("Concurrent Users")
        ax.set_ylabel("Error Rate (%)")
        ax.set_title("Error Rate vs Concurrent Users")
        ax.legend()
        ax.grid(True, alpha=0.3)

    def print_summary(self):
        """Print performance summary"""
        print("\n=== Performance Summary ===")

        for users in USER_COUNTS:
            print(f"\n{users} Concurrent Users:")
            user_data = self.df[self.df["users"] == users]

            for backend in user_data["backend"].unique():
                backend_data = user_data[user_data["backend"] == backend].iloc[0]
                print(f"  {backend} Backend:")
                print(
                    f"    Avg Response Time: {backend_data['avg_response_time']:.3f}s"
                )
                print(
                    f"    P95 Response Time: {backend_data['p95_response_time']:.3f}s"
                )
                print(f"    Throughput: {backend_data['throughput_rps']:.1f} req/s")
                print(f"    Error Rate: {backend_data['error_rate']:.1f}%")

        # Calculate overall improvements
        self._calculate_improvements()

    def _calculate_improvements(self):
        """Calculate performance improvements"""
        print("\n=== Performance Improvements (New vs Old) ===")

        old_data = self.df[self.df["backend"] == "Old"]
        new_data = self.df[self.df["backend"] == "New"]

        if len(old_data) > 0 and len(new_data) > 0:
            for users in USER_COUNTS:
                old_user = old_data[old_data["users"] == users]
                new_user = new_data[new_data["users"] == users]

                if len(old_user) > 0 and len(new_user) > 0:
                    old_row = old_user.iloc[0]
                    new_row = new_user.iloc[0]

                    # Calculate improvements (negative = better for response time, positive = better for throughput)
                    resp_time_improvement = (
                        (old_row["avg_response_time"] - new_row["avg_response_time"])
                        / old_row["avg_response_time"]
                    ) * 100
                    throughput_improvement = (
                        (new_row["throughput_rps"] - old_row["throughput_rps"])
                        / old_row["throughput_rps"]
                    ) * 100

                    print(f"\n{users} Users:")
                    print(f"  Response Time: {resp_time_improvement:+.1f}%")
                    print(f"  Throughput: {throughput_improvement:+.1f}%")


# =============================================================================
# MAIN EXECUTION
# =============================================================================


async def main():
    """Main execution"""
    print("Starting Backend Performance Comparison...")
    print(f"Old Backend: {OLD_BACKEND_URL}")
    print(f"New Backend: {NEW_BACKEND_URL}")

    # Run benchmark
    engine = BenchmarkEngine()
    results = await engine.run_benchmark()

    if results:
        # Create visualizations
        visualizer = BenchmarkVisualizer(results)
        visualizer.create_comparison_charts()
        visualizer.print_summary()

        print("\n Benchmark completed successfully!")
        print("Check the generated PNG file for visual comparison.")
    else:
        print("No results obtained. Check if both backends are running.")


if __name__ == "__main__":
    asyncio.run(main())
