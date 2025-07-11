#!/usr/bin/env python3
"""
Comprehensive Backend Performance Benchmark Suite
Compares Old Backend (Flask/Quart) vs New Backend (FastAPI) Performance

Features:
- Response time analysis
- Concurrent user load testing
- Throughput measurement
- Error rate tracking
- Statistical analysis
- Beautiful visualization charts
- Detailed performance reports

Focus Areas:
- /chat endpoint performance
- /vote endpoint performance
- Scalability under load
- Response consistency
"""

import asyncio
import aiohttp
import time
import json
import statistics
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

# =============================================================================
# CONFIGURATION - UPDATE THESE URLs
# =============================================================================

# Backend URLs - REAL BACKEND ENDPOINTS (NO MOCKS)
OLD_BACKEND_URL = "http://localhost:5000"  # Your Flask/Quart backend
NEW_BACKEND_URL = "http://localhost:8000"  # Your FastAPI backend

# Test Configuration
MAX_CONCURRENT_USERS = [1, 5, 10, 20, 50, 100]  # Concurrent user levels to test
REQUESTS_PER_USER = 10  # Number of requests each user makes
WARMUP_REQUESTS = 5  # Warmup requests before measuring
TEST_TIMEOUT = 300  # Maximum test duration in seconds

# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class TestResult:
    """Individual test result"""

    endpoint: str
    backend: str
    response_time: float
    status_code: int
    success: bool
    payload_size: int
    timestamp: datetime
    concurrent_users: int
    error_message: str = None


@dataclass
class EndpointStats:
    """Aggregated statistics for an endpoint"""

    endpoint: str
    backend: str
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput_rps: float
    error_rate: float
    total_bytes: int


@dataclass
class BenchmarkSummary:
    """Complete benchmark summary"""

    test_date: datetime
    duration: float
    old_backend_stats: List[EndpointStats]
    new_backend_stats: List[EndpointStats]
    performance_improvements: Dict[str, Dict[str, float]]


# =============================================================================
# TEST DATA GENERATORS
# =============================================================================


class TestDataGenerator:
    """Generates realistic test data for API endpoints"""

    SAMPLE_QUESTIONS = [
        "What is the company's vacation policy?",
        "How do I report sick leave?",
        "What are the benefits available to employees?",
        "How do I access my pay stub?",
        "What is the remote work policy?",
        "How do I request time off?",
        "What are the office hours?",
        "How do I contact HR?",
        "What is the dress code policy?",
        "How do I submit an expense report?",
        "What training programs are available?",
        "How do I change my personal information?",
        "What is the performance review process?",
        "How do I refer a candidate?",
        "What is the company's diversity policy?",
    ]

    SAMPLE_RESPONSES = [
        "Based on the company policy, employees receive 15 days of paid vacation annually.",
        "To report sick leave, please contact your manager and HR department.",
        "The company offers comprehensive health, dental, and vision insurance.",
        "You can access your pay stub through the employee portal.",
        "Remote work is allowed up to 3 days per week with manager approval.",
        "Time off requests should be submitted through the HR system at least 2 weeks in advance.",
        "Standard office hours are 9 AM to 5 PM, Monday through Friday.",
        "You can contact HR at hr@company.com or extension 1234.",
        "Business casual attire is required in the office.",
        "Expense reports should be submitted monthly through the finance portal.",
    ]

    @classmethod
    def generate_chat_request(cls) -> Dict[str, Any]:
        """Generate a realistic chat request"""
        question = random.choice(cls.SAMPLE_QUESTIONS)
        return {
            "messages": [{"role": "user", "content": question}],
            "stream": False,
            "context": {
                "overrides": {
                    "semantic_ranker": True,
                    "semantic_captions": True,
                    "top": 3,
                    "suggest_followup_questions": False,
                }
            },
        }

    @classmethod
    def generate_vote_request(cls) -> Dict[str, Any]:
        """Generate a realistic vote request"""
        question = random.choice(cls.SAMPLE_QUESTIONS)
        response = random.choice(cls.SAMPLE_RESPONSES)
        is_upvote = random.choice([True, False])

        base_vote = {
            "user_query": question,
            "chatbot_response": response,
            "upvote": 1 if is_upvote else 0,
            "downvote": 0 if is_upvote else 1,
            "count": 1,
            "data": datetime.now().strftime("%m/%d/%y"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "email_address": f"user{random.randint(1, 1000)}@company.com",
        }

        # Add downvote-specific fields if it's a downvote
        if not is_upvote:
            base_vote.update(
                {
                    "reason_multiple_choice": random.choice(
                        ["Incorrect information", "Not helpful", "Too vague", "Other"]
                    ),
                    "additional_comments": "This response could be improved.",
                }
            )

        return base_vote


# =============================================================================
# BENCHMARK ENGINE
# =============================================================================


class BenchmarkEngine:
    """Main benchmark engine for performance testing"""

    def __init__(self):
        self.session: aiohttp.ClientSession = None
        self.results: List[TestResult] = []
        self.start_time: datetime = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def make_request(
        self,
        backend_url: str,
        endpoint: str,
        payload: Dict[str, Any],
        concurrent_users: int,
    ) -> TestResult:
        """Make a single API request and measure performance"""
        url = f"{backend_url}{endpoint}"
        start_time = time.time()

        try:
            async with self.session.post(
                url, json=payload, headers={"Content-Type": "application/json"}
            ) as response:
                response_data = await response.read()
                end_time = time.time()

                return TestResult(
                    endpoint=endpoint,
                    backend=backend_url,
                    response_time=(end_time - start_time) * 1000,  # Convert to ms
                    status_code=response.status,
                    success=response.status < 400,
                    payload_size=len(response_data),
                    timestamp=datetime.now(),
                    concurrent_users=concurrent_users,
                )

        except Exception as e:
            end_time = time.time()
            return TestResult(
                endpoint=endpoint,
                backend=backend_url,
                response_time=(end_time - start_time) * 1000,
                status_code=0,
                success=False,
                payload_size=0,
                timestamp=datetime.now(),
                concurrent_users=concurrent_users,
                error_message=str(e),
            )

    async def run_user_simulation(
        self, backend_url: str, concurrent_users: int, user_id: int
    ) -> List[TestResult]:
        """Simulate a single user making multiple requests"""
        user_results = []

        # Mix of chat and vote requests
        for request_num in range(REQUESTS_PER_USER):
            if request_num % 2 == 0:  # Chat request
                payload = TestDataGenerator.generate_chat_request()
                endpoint = "/chat"
            else:  # Vote request
                payload = TestDataGenerator.generate_vote_request()
                endpoint = "/vote"

            result = await self.make_request(
                backend_url, endpoint, payload, concurrent_users
            )
            user_results.append(result)

            # Small delay between requests to simulate real user behavior
            await asyncio.sleep(random.uniform(0.5, 2.0))

        return user_results

    async def run_load_test(
        self, backend_url: str, concurrent_users: int
    ) -> List[TestResult]:
        """Run load test with specified number of concurrent users"""
        print(
            f"🔥 Running load test: {concurrent_users} concurrent users on {backend_url}"
        )

        # Warmup phase
        print(f"   🌡️  Warming up with {WARMUP_REQUESTS} requests...")
        warmup_tasks = []
        for i in range(WARMUP_REQUESTS):
            payload = TestDataGenerator.generate_chat_request()
            task = self.make_request(backend_url, "/chat", payload, 1)
            warmup_tasks.append(task)

        await asyncio.gather(*warmup_tasks, return_exceptions=True)

        # Main load test
        print(f"   ⚡ Starting main load test...")
        start_time = time.time()

        # Create tasks for concurrent users
        tasks = []
        for user_id in range(concurrent_users):
            task = self.run_user_simulation(backend_url, concurrent_users, user_id)
            tasks.append(task)

        # Execute all user simulations concurrently
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        all_results = []
        for results_list in results_lists:
            if isinstance(results_list, list):
                all_results.extend(results_list)
            else:
                print(f"   ⚠️  Error in user simulation: {results_list}")

        end_time = time.time()
        duration = end_time - start_time

        successful_results = [r for r in all_results if r.success]
        total_requests = len(all_results)
        successful_requests = len(successful_results)

        print(
            f"   ✅ Completed: {successful_requests}/{total_requests} successful in {duration:.2f}s"
        )

        return all_results

    async def run_full_benchmark(self) -> BenchmarkSummary:
        """Run complete benchmark suite"""
        self.start_time = datetime.now()
        print("🚀 Starting Comprehensive Backend Benchmark Suite")
        print("=" * 60)

        all_results = []

        # Test both backends with different concurrent user levels
        for concurrent_users in MAX_CONCURRENT_USERS:
            print(f"\n📊 Testing with {concurrent_users} concurrent users")
            print("-" * 40)

            # Test old backend
            old_results = await self.run_load_test(OLD_BACKEND_URL, concurrent_users)
            all_results.extend(old_results)

            # Small delay between backend tests
            await asyncio.sleep(2)

            # Test new backend
            new_results = await self.run_load_test(NEW_BACKEND_URL, concurrent_users)
            all_results.extend(new_results)

            # Delay before next test level
            await asyncio.sleep(5)

        self.results = all_results

        # Generate statistics and summary
        summary = self._generate_summary()

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        summary.duration = duration

        print(f"\n🎉 Benchmark completed in {duration:.2f} seconds")
        print(f"📈 Total requests: {len(all_results)}")

        return summary

    def _generate_summary(self) -> BenchmarkSummary:
        """Generate comprehensive benchmark summary"""
        old_stats = []
        new_stats = []

        # Group results by backend, endpoint, and concurrent users
        grouped_results = {}
        for result in self.results:
            key = (result.backend, result.endpoint, result.concurrent_users)
            if key not in grouped_results:
                grouped_results[key] = []
            grouped_results[key].append(result)

        # Calculate statistics for each group
        for (backend, endpoint, concurrent_users), results in grouped_results.items():
            stats = self._calculate_stats(results, endpoint, backend, concurrent_users)

            if OLD_BACKEND_URL in backend:
                old_stats.append(stats)
            else:
                new_stats.append(stats)

        # Calculate performance improvements
        improvements = self._calculate_improvements(old_stats, new_stats)

        return BenchmarkSummary(
            test_date=self.start_time,
            duration=0,  # Will be set later
            old_backend_stats=old_stats,
            new_backend_stats=new_stats,
            performance_improvements=improvements,
        )

    def _calculate_stats(
        self,
        results: List[TestResult],
        endpoint: str,
        backend: str,
        concurrent_users: int,
    ) -> EndpointStats:
        """Calculate statistics for a group of results"""
        successful_results = [r for r in results if r.success]
        response_times = [r.response_time for r in successful_results]

        if not response_times:
            response_times = [0]

        total_bytes = sum(r.payload_size for r in successful_results)
        duration = 0
        if len(results) > 1:
            timestamps = [r.timestamp for r in results]
            duration = (max(timestamps) - min(timestamps)).total_seconds()
            if duration == 0:
                duration = 1  # Avoid division by zero
        else:
            duration = 1

        throughput = len(successful_results) / duration if duration > 0 else 0

        return EndpointStats(
            endpoint=endpoint,
            backend=backend,
            concurrent_users=concurrent_users,
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(results) - len(successful_results),
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=statistics.median(response_times),
            p95_response_time=(
                np.percentile(response_times, 95) if response_times else 0
            ),
            p99_response_time=(
                np.percentile(response_times, 99) if response_times else 0
            ),
            throughput_rps=throughput,
            error_rate=(len(results) - len(successful_results)) / len(results) * 100,
            total_bytes=total_bytes,
        )

    def _calculate_improvements(
        self, old_stats: List[EndpointStats], new_stats: List[EndpointStats]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate performance improvements from old to new backend"""
        improvements = {}

        # Group by endpoint and concurrent users
        old_grouped = {}
        new_grouped = {}

        for stat in old_stats:
            key = (stat.endpoint, stat.concurrent_users)
            old_grouped[key] = stat

        for stat in new_stats:
            key = (stat.endpoint, stat.concurrent_users)
            new_grouped[key] = stat

        # Calculate improvements for matching keys
        for key in old_grouped:
            if key in new_grouped:
                old_stat = old_grouped[key]
                new_stat = new_grouped[key]

                endpoint_key = f"{key[0]}_{key[1]}users"

                # Calculate percentage improvements (negative means worse performance)
                improvements[endpoint_key] = {
                    "avg_response_time": self._calc_improvement_percent(
                        old_stat.avg_response_time,
                        new_stat.avg_response_time,
                        lower_is_better=True,
                    ),
                    "p95_response_time": self._calc_improvement_percent(
                        old_stat.p95_response_time,
                        new_stat.p95_response_time,
                        lower_is_better=True,
                    ),
                    "throughput": self._calc_improvement_percent(
                        old_stat.throughput_rps,
                        new_stat.throughput_rps,
                        lower_is_better=False,
                    ),
                    "error_rate": self._calc_improvement_percent(
                        old_stat.error_rate, new_stat.error_rate, lower_is_better=True
                    ),
                }

        return improvements

    def _calc_improvement_percent(
        self, old_value: float, new_value: float, lower_is_better: bool = True
    ) -> float:
        """Calculate improvement percentage"""
        if old_value == 0:
            return 0

        if lower_is_better:
            # For metrics where lower is better (response time, error rate)
            improvement = ((old_value - new_value) / old_value) * 100
        else:
            # For metrics where higher is better (throughput)
            improvement = ((new_value - old_value) / old_value) * 100

        return improvement


# =============================================================================
# VISUALIZATION AND REPORTING
# =============================================================================


class BenchmarkVisualizer:
    """Generate beautiful charts and reports from benchmark results"""

    def __init__(self, summary: BenchmarkSummary, results: List[TestResult]):
        self.summary = summary
        self.results = results
        self.output_dir = Path("benchmark_results")
        self.output_dir.mkdir(exist_ok=True)

        # Set up plotting style
        plt.style.use("seaborn-v0_8-whitegrid")
        sns.set_palette("husl")

    def generate_all_charts(self):
        """Generate all visualization charts"""
        print("\n📊 Generating performance charts...")

        self._plot_response_time_comparison()
        self._plot_throughput_comparison()
        self._plot_concurrent_users_scaling()
        self._plot_error_rates()
        self._plot_response_time_distribution()
        self._plot_performance_heatmap()
        self._generate_summary_report()

        print(f"📁 All charts saved to: {self.output_dir}")

    def _plot_response_time_comparison(self):
        """Plot response time comparison between backends"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Response Time Comparison: Old vs New Backend",
            fontsize=16,
            fontweight="bold",
        )

        # Prepare data
        old_chat_stats = [
            s for s in self.summary.old_backend_stats if s.endpoint == "/chat"
        ]
        new_chat_stats = [
            s for s in self.summary.new_backend_stats if s.endpoint == "/chat"
        ]
        old_vote_stats = [
            s for s in self.summary.old_backend_stats if s.endpoint == "/vote"
        ]
        new_vote_stats = [
            s for s in self.summary.new_backend_stats if s.endpoint == "/vote"
        ]

        # Chat endpoint - Average response time
        if old_chat_stats and new_chat_stats:
            users = [s.concurrent_users for s in old_chat_stats]
            old_times = [s.avg_response_time for s in old_chat_stats]
            new_times = [s.avg_response_time for s in new_chat_stats]

            ax1.plot(
                users, old_times, "o-", label="Old Backend", linewidth=2, markersize=8
            )
            ax1.plot(
                users, new_times, "s-", label="New Backend", linewidth=2, markersize=8
            )
            ax1.set_title("/chat - Average Response Time", fontweight="bold")
            ax1.set_xlabel("Concurrent Users")
            ax1.set_ylabel("Response Time (ms)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # Chat endpoint - P95 response time
        if old_chat_stats and new_chat_stats:
            old_p95 = [s.p95_response_time for s in old_chat_stats]
            new_p95 = [s.p95_response_time for s in new_chat_stats]

            ax2.plot(
                users, old_p95, "o-", label="Old Backend", linewidth=2, markersize=8
            )
            ax2.plot(
                users, new_p95, "s-", label="New Backend", linewidth=2, markersize=8
            )
            ax2.set_title("/chat - P95 Response Time", fontweight="bold")
            ax2.set_xlabel("Concurrent Users")
            ax2.set_ylabel("Response Time (ms)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        # Vote endpoint - Average response time
        if old_vote_stats and new_vote_stats:
            users = [s.concurrent_users for s in old_vote_stats]
            old_times = [s.avg_response_time for s in old_vote_stats]
            new_times = [s.avg_response_time for s in new_vote_stats]

            ax3.plot(
                users, old_times, "o-", label="Old Backend", linewidth=2, markersize=8
            )
            ax3.plot(
                users, new_times, "s-", label="New Backend", linewidth=2, markersize=8
            )
            ax3.set_title("/vote - Average Response Time", fontweight="bold")
            ax3.set_xlabel("Concurrent Users")
            ax3.set_ylabel("Response Time (ms)")
            ax3.legend()
            ax3.grid(True, alpha=0.3)

        # Vote endpoint - P95 response time
        if old_vote_stats and new_vote_stats:
            old_p95 = [s.p95_response_time for s in old_vote_stats]
            new_p95 = [s.p95_response_time for s in new_vote_stats]

            ax4.plot(
                users, old_p95, "o-", label="Old Backend", linewidth=2, markersize=8
            )
            ax4.plot(
                users, new_p95, "s-", label="New Backend", linewidth=2, markersize=8
            )
            ax4.set_title("/vote - P95 Response Time", fontweight="bold")
            ax4.set_xlabel("Concurrent Users")
            ax4.set_ylabel("Response Time (ms)")
            ax4.legend()
            ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "response_time_comparison.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    def _plot_throughput_comparison(self):
        """Plot throughput comparison"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle(
            "Throughput Comparison: Requests per Second", fontsize=16, fontweight="bold"
        )

        # Chat endpoint throughput
        old_chat_stats = [
            s for s in self.summary.old_backend_stats if s.endpoint == "/chat"
        ]
        new_chat_stats = [
            s for s in self.summary.new_backend_stats if s.endpoint == "/chat"
        ]

        if old_chat_stats and new_chat_stats:
            users = [s.concurrent_users for s in old_chat_stats]
            old_throughput = [s.throughput_rps for s in old_chat_stats]
            new_throughput = [s.throughput_rps for s in new_chat_stats]

            ax1.bar(
                [u - 0.2 for u in users],
                old_throughput,
                0.4,
                label="Old Backend",
                alpha=0.8,
            )
            ax1.bar(
                [u + 0.2 for u in users],
                new_throughput,
                0.4,
                label="New Backend",
                alpha=0.8,
            )
            ax1.set_title("/chat Endpoint Throughput", fontweight="bold")
            ax1.set_xlabel("Concurrent Users")
            ax1.set_ylabel("Requests per Second")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # Vote endpoint throughput
        old_vote_stats = [
            s for s in self.summary.old_backend_stats if s.endpoint == "/vote"
        ]
        new_vote_stats = [
            s for s in self.summary.new_backend_stats if s.endpoint == "/vote"
        ]

        if old_vote_stats and new_vote_stats:
            users = [s.concurrent_users for s in old_vote_stats]
            old_throughput = [s.throughput_rps for s in old_vote_stats]
            new_throughput = [s.throughput_rps for s in new_vote_stats]

            ax2.bar(
                [u - 0.2 for u in users],
                old_throughput,
                0.4,
                label="Old Backend",
                alpha=0.8,
            )
            ax2.bar(
                [u + 0.2 for u in users],
                new_throughput,
                0.4,
                label="New Backend",
                alpha=0.8,
            )
            ax2.set_title("/vote Endpoint Throughput", fontweight="bold")
            ax2.set_xlabel("Concurrent Users")
            ax2.set_ylabel("Requests per Second")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "throughput_comparison.png", dpi=300, bbox_inches="tight"
        )
        plt.close()

    def _plot_concurrent_users_scaling(self):
        """Plot how performance scales with concurrent users"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Performance Scaling with Concurrent Users", fontsize=16, fontweight="bold"
        )

        # Prepare data for all endpoints
        endpoints = ["/chat", "/vote"]
        colors = ["blue", "red"]

        for i, endpoint in enumerate(endpoints):
            old_stats = [
                s for s in self.summary.old_backend_stats if s.endpoint == endpoint
            ]
            new_stats = [
                s for s in self.summary.new_backend_stats if s.endpoint == endpoint
            ]

            if old_stats and new_stats:
                users = [s.concurrent_users for s in old_stats]

                # Response time scaling
                old_times = [s.avg_response_time for s in old_stats]
                new_times = [s.avg_response_time for s in new_stats]

                ax1.plot(
                    users,
                    old_times,
                    "o-",
                    label=f"Old - {endpoint}",
                    color=colors[i],
                    alpha=0.7,
                    linewidth=2,
                )
                ax2.plot(
                    users,
                    new_times,
                    "s-",
                    label=f"New - {endpoint}",
                    color=colors[i],
                    alpha=0.7,
                    linewidth=2,
                )

                # Throughput scaling
                old_throughput = [s.throughput_rps for s in old_stats]
                new_throughput = [s.throughput_rps for s in new_stats]

                ax3.plot(
                    users,
                    old_throughput,
                    "o-",
                    label=f"Old - {endpoint}",
                    color=colors[i],
                    alpha=0.7,
                    linewidth=2,
                )
                ax4.plot(
                    users,
                    new_throughput,
                    "s-",
                    label=f"New - {endpoint}",
                    color=colors[i],
                    alpha=0.7,
                    linewidth=2,
                )

        ax1.set_title("Old Backend - Response Time Scaling", fontweight="bold")
        ax1.set_xlabel("Concurrent Users")
        ax1.set_ylabel("Avg Response Time (ms)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.set_title("New Backend - Response Time Scaling", fontweight="bold")
        ax2.set_xlabel("Concurrent Users")
        ax2.set_ylabel("Avg Response Time (ms)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        ax3.set_title("Old Backend - Throughput Scaling", fontweight="bold")
        ax3.set_xlabel("Concurrent Users")
        ax3.set_ylabel("Throughput (RPS)")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        ax4.set_title("New Backend - Throughput Scaling", fontweight="bold")
        ax4.set_xlabel("Concurrent Users")
        ax4.set_ylabel("Throughput (RPS)")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "scaling_analysis.png", dpi=300, bbox_inches="tight"
        )
        plt.close()

    def _plot_error_rates(self):
        """Plot error rates comparison"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle("Error Rate Comparison", fontsize=16, fontweight="bold")

        # Chat endpoint error rates
        old_chat_stats = [
            s for s in self.summary.old_backend_stats if s.endpoint == "/chat"
        ]
        new_chat_stats = [
            s for s in self.summary.new_backend_stats if s.endpoint == "/chat"
        ]

        if old_chat_stats and new_chat_stats:
            users = [s.concurrent_users for s in old_chat_stats]
            old_errors = [s.error_rate for s in old_chat_stats]
            new_errors = [s.error_rate for s in new_chat_stats]

            x = np.arange(len(users))
            width = 0.35

            ax1.bar(
                x - width / 2,
                old_errors,
                width,
                label="Old Backend",
                alpha=0.8,
                color="red",
            )
            ax1.bar(
                x + width / 2,
                new_errors,
                width,
                label="New Backend",
                alpha=0.8,
                color="green",
            )
            ax1.set_title("/chat Endpoint Error Rate", fontweight="bold")
            ax1.set_xlabel("Concurrent Users")
            ax1.set_ylabel("Error Rate (%)")
            ax1.set_xticks(x)
            ax1.set_xticklabels(users)
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # Vote endpoint error rates
        old_vote_stats = [
            s for s in self.summary.old_backend_stats if s.endpoint == "/vote"
        ]
        new_vote_stats = [
            s for s in self.summary.new_backend_stats if s.endpoint == "/vote"
        ]

        if old_vote_stats and new_vote_stats:
            users = [s.concurrent_users for s in old_vote_stats]
            old_errors = [s.error_rate for s in old_vote_stats]
            new_errors = [s.error_rate for s in new_vote_stats]

            x = np.arange(len(users))

            ax2.bar(
                x - width / 2,
                old_errors,
                width,
                label="Old Backend",
                alpha=0.8,
                color="red",
            )
            ax2.bar(
                x + width / 2,
                new_errors,
                width,
                label="New Backend",
                alpha=0.8,
                color="green",
            )
            ax2.set_title("/vote Endpoint Error Rate", fontweight="bold")
            ax2.set_xlabel("Concurrent Users")
            ax2.set_ylabel("Error Rate (%)")
            ax2.set_xticks(x)
            ax2.set_xticklabels(users)
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / "error_rates.png", dpi=300, bbox_inches="tight")
        plt.close()

    def _plot_response_time_distribution(self):
        """Plot response time distribution"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Response Time Distribution Analysis", fontsize=16, fontweight="bold"
        )

        # Prepare data
        old_chat_results = [
            r
            for r in self.results
            if "/chat" in r.endpoint and OLD_BACKEND_URL in r.backend and r.success
        ]
        new_chat_results = [
            r
            for r in self.results
            if "/chat" in r.endpoint and NEW_BACKEND_URL in r.backend and r.success
        ]
        old_vote_results = [
            r
            for r in self.results
            if "/vote" in r.endpoint and OLD_BACKEND_URL in r.backend and r.success
        ]
        new_vote_results = [
            r
            for r in self.results
            if "/vote" in r.endpoint and NEW_BACKEND_URL in r.backend and r.success
        ]

        # Chat endpoint histograms
        if old_chat_results and new_chat_results:
            old_times = [r.response_time for r in old_chat_results]
            new_times = [r.response_time for r in new_chat_results]

            ax1.hist(
                old_times,
                bins=30,
                alpha=0.7,
                label="Old Backend",
                color="red",
                density=True,
            )
            ax1.hist(
                new_times,
                bins=30,
                alpha=0.7,
                label="New Backend",
                color="blue",
                density=True,
            )
            ax1.set_title("/chat Response Time Distribution", fontweight="bold")
            ax1.set_xlabel("Response Time (ms)")
            ax1.set_ylabel("Density")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # Vote endpoint histograms
        if old_vote_results and new_vote_results:
            old_times = [r.response_time for r in old_vote_results]
            new_times = [r.response_time for r in new_vote_results]

            ax2.hist(
                old_times,
                bins=30,
                alpha=0.7,
                label="Old Backend",
                color="red",
                density=True,
            )
            ax2.hist(
                new_times,
                bins=30,
                alpha=0.7,
                label="New Backend",
                color="blue",
                density=True,
            )
            ax2.set_title("/vote Response Time Distribution", fontweight="bold")
            ax2.set_xlabel("Response Time (ms)")
            ax2.set_ylabel("Density")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        # Box plots for comparison
        if old_chat_results and new_chat_results:
            old_times = [r.response_time for r in old_chat_results]
            new_times = [r.response_time for r in new_chat_results]

            ax3.boxplot([old_times, new_times], labels=["Old Backend", "New Backend"])
            ax3.set_title("/chat Response Time Box Plot", fontweight="bold")
            ax3.set_ylabel("Response Time (ms)")
            ax3.grid(True, alpha=0.3)

        if old_vote_results and new_vote_results:
            old_times = [r.response_time for r in old_vote_results]
            new_times = [r.response_time for r in new_vote_results]

            ax4.boxplot([old_times, new_times], labels=["Old Backend", "New Backend"])
            ax4.set_title("/vote Response Time Box Plot", fontweight="bold")
            ax4.set_ylabel("Response Time (ms)")
            ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "response_time_distribution.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    def _plot_performance_heatmap(self):
        """Create performance improvement heatmap"""
        if not self.summary.performance_improvements:
            return

        # Prepare data for heatmap
        metrics = ["avg_response_time", "p95_response_time", "throughput", "error_rate"]
        metric_labels = [
            "Avg Response Time",
            "P95 Response Time",
            "Throughput",
            "Error Rate",
        ]

        test_scenarios = list(self.summary.performance_improvements.keys())

        heatmap_data = []
        for scenario in test_scenarios:
            row = []
            for metric in metrics:
                improvement = self.summary.performance_improvements[scenario].get(
                    metric, 0
                )
                row.append(improvement)
            heatmap_data.append(row)

        # Create heatmap
        fig, ax = plt.subplots(figsize=(12, 8))

        # Create custom colormap (red for worse, green for better)
        from matplotlib.colors import LinearSegmentedColormap

        colors = ["red", "white", "green"]
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list("improvement", colors, N=n_bins)

        im = ax.imshow(heatmap_data, cmap=cmap, aspect="auto", vmin=-50, vmax=50)

        # Set ticks and labels
        ax.set_xticks(np.arange(len(metric_labels)))
        ax.set_yticks(np.arange(len(test_scenarios)))
        ax.set_xticklabels(metric_labels)
        ax.set_yticklabels(test_scenarios)

        # Rotate the tick labels and set their alignment
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # Add text annotations
        for i in range(len(test_scenarios)):
            for j in range(len(metric_labels)):
                text = ax.text(
                    j,
                    i,
                    f"{heatmap_data[i][j]:.1f}%",
                    ha="center",
                    va="center",
                    color="black",
                    fontweight="bold",
                )

        ax.set_title(
            "Performance Improvement Heatmap\n(Green = Better, Red = Worse)",
            fontsize=14,
            fontweight="bold",
        )

        # Add colorbar
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel("Improvement Percentage", rotation=-90, va="bottom")

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "performance_heatmap.png", dpi=300, bbox_inches="tight"
        )
        plt.close()

    def _generate_summary_report(self):
        """Generate detailed text summary report"""
        report_path = self.output_dir / "benchmark_summary_report.txt"

        with open(report_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("COMPREHENSIVE BACKEND PERFORMANCE BENCHMARK REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write(
                f"Test Date: {self.summary.test_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"Test Duration: {self.summary.duration:.2f} seconds\n")
            f.write(f"Total Requests: {len(self.results)}\n\n")

            f.write("BACKEND CONFIGURATIONS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Old Backend (Flask/Quart): {OLD_BACKEND_URL}\n")
            f.write(f"New Backend (FastAPI): {NEW_BACKEND_URL}\n\n")

            f.write("TEST SCENARIOS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Concurrent User Levels: {MAX_CONCURRENT_USERS}\n")
            f.write(f"Requests per User: {REQUESTS_PER_USER}\n")
            f.write(f"Endpoints Tested: /chat, /vote\n\n")

            # Summary statistics
            f.write("PERFORMANCE SUMMARY:\n")
            f.write("-" * 40 + "\n")

            successful_requests = len([r for r in self.results if r.success])
            total_requests = len(self.results)
            overall_success_rate = (successful_requests / total_requests) * 100

            f.write(f"Overall Success Rate: {overall_success_rate:.2f}%\n")
            f.write(f"Successful Requests: {successful_requests}/{total_requests}\n\n")

            # Performance improvements
            if self.summary.performance_improvements:
                f.write("PERFORMANCE IMPROVEMENTS (New vs Old Backend):\n")
                f.write("-" * 60 + "\n")

                for (
                    scenario,
                    improvements,
                ) in self.summary.performance_improvements.items():
                    f.write(f"\n{scenario}:\n")
                    for metric, improvement in improvements.items():
                        status = (
                            "🚀 IMPROVED"
                            if improvement > 0
                            else "⚠️  DEGRADED" if improvement < 0 else "➡️  UNCHANGED"
                        )
                        f.write(f"  {metric}: {improvement:+.2f}% {status}\n")

            # Detailed statistics
            f.write("\n\nDETAILED STATISTICS:\n")
            f.write("=" * 60 + "\n")

            f.write("\nOLD BACKEND STATISTICS:\n")
            f.write("-" * 40 + "\n")
            for stat in self.summary.old_backend_stats:
                f.write(
                    f"\n{stat.endpoint} - {stat.concurrent_users} concurrent users:\n"
                )
                f.write(
                    f"  Requests: {stat.total_requests} (Success: {stat.successful_requests}, Failed: {stat.failed_requests})\n"
                )
                f.write(
                    f"  Response Time: Avg={stat.avg_response_time:.2f}ms, P95={stat.p95_response_time:.2f}ms\n"
                )
                f.write(f"  Throughput: {stat.throughput_rps:.2f} RPS\n")
                f.write(f"  Error Rate: {stat.error_rate:.2f}%\n")

            f.write("\n\nNEW BACKEND STATISTICS:\n")
            f.write("-" * 40 + "\n")
            for stat in self.summary.new_backend_stats:
                f.write(
                    f"\n{stat.endpoint} - {stat.concurrent_users} concurrent users:\n"
                )
                f.write(
                    f"  Requests: {stat.total_requests} (Success: {stat.successful_requests}, Failed: {stat.failed_requests})\n"
                )
                f.write(
                    f"  Response Time: Avg={stat.avg_response_time:.2f}ms, P95={stat.p95_response_time:.2f}ms\n"
                )
                f.write(f"  Throughput: {stat.throughput_rps:.2f} RPS\n")
                f.write(f"  Error Rate: {stat.error_rate:.2f}%\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")


# =============================================================================
# MAIN EXECUTION
# =============================================================================


async def main():
    """Main execution function"""
    print("🎯 Backend Performance Benchmark Suite")
    print("📊 Comparing Old Backend vs New Backend Performance")
    print(f"🔗 Old Backend: {OLD_BACKEND_URL}")
    print(f"🔗 New Backend: {NEW_BACKEND_URL}")
    print()

    # Check if URLs are configured
    if "your-old-backend" in OLD_BACKEND_URL or "your-new-backend" in NEW_BACKEND_URL:
        print("⚠️  Please update the backend URLs in the script before running!")
        print(
            "Edit the OLD_BACKEND_URL and NEW_BACKEND_URL variables at the top of the script."
        )
        return

    # Install required packages if needed
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pandas as pd
        import numpy as np
    except ImportError:
        print("📦 Installing required visualization packages...")
        import subprocess
        import sys

        packages = ["matplotlib", "seaborn", "pandas", "numpy"]
        for package in packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

        print("✅ Packages installed successfully!")
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pandas as pd
        import numpy as np

    # Run benchmark
    async with BenchmarkEngine() as engine:
        summary = await engine.run_full_benchmark()

        # Generate visualizations
        visualizer = BenchmarkVisualizer(summary, engine.results)
        visualizer.generate_all_charts()

        print("\n🎉 Benchmark Complete!")
        print(f"📊 Results saved to: {visualizer.output_dir}")
        print("\nGenerated files:")
        for file in visualizer.output_dir.glob("*.png"):
            print(f"  📈 {file.name}")
        print(f"  📝 benchmark_summary_report.txt")


if __name__ == "__main__":
    asyncio.run(main())
