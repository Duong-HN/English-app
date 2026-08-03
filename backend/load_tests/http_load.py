"""Run a small concurrent HTTP baseline against a deployed LearnMate API.

This is intentionally dependency-free so it can be used from a clean Python
environment. It is a smoke/load baseline, not a replacement for a sustained
test with realistic user journeys, arrival rates, and production observability.
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RequestResult:
    latency_ms: float
    status_code: int | None
    error: str | None = None


@dataclass(frozen=True)
class LoadSummary:
    total_requests: int
    successful_requests: int
    failed_requests: int
    elapsed_seconds: float
    latencies_ms: tuple[float, ...]

    @property
    def throughput_per_second(self) -> float:
        return self.total_requests / self.elapsed_seconds if self.elapsed_seconds else 0.0

    @property
    def error_rate(self) -> float:
        return self.failed_requests / self.total_requests if self.total_requests else 0.0

    def percentile_ms(self, percentile: float) -> float:
        if not 0 < percentile <= 100:
            raise ValueError("percentile must be between 0 and 100")
        if not self.latencies_ms:
            return 0.0
        ordered = sorted(self.latencies_ms)
        index = min(len(ordered) - 1, max(0, round((percentile / 100) * len(ordered) + 0.5) - 1))
        return ordered[index]


def _request(url: str, timeout_seconds: float, bearer_token: str | None) -> RequestResult:
    started = time.perf_counter()
    headers = {"Accept": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response.read()
            status_code = response.status
            error = None if 200 <= status_code < 300 else f"HTTP {status_code}"
    except HTTPError as exc:
        status_code = exc.code
        error = f"HTTP {exc.code}"
    except (TimeoutError, URLError, OSError) as exc:
        status_code = None
        error = str(exc)
    return RequestResult((time.perf_counter() - started) * 1000, status_code, error)


def run_load(
    base_url: str,
    endpoint: str = "/health/live",
    total_requests: int = 100,
    concurrency: int = 10,
    timeout_seconds: float = 5.0,
    bearer_token: str | None = None,
) -> LoadSummary:
    """Issue concurrent GET requests and return latency/error statistics."""
    if total_requests < 1:
        raise ValueError("total_requests must be at least 1")
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(
            executor.map(
                lambda _: _request(url, timeout_seconds, bearer_token),
                range(total_requests),
            )
        )
    elapsed_seconds = time.perf_counter() - started
    successful = sum(1 for result in results if result.error is None)
    return LoadSummary(
        total_requests=total_requests,
        successful_requests=successful,
        failed_requests=total_requests - successful,
        elapsed_seconds=elapsed_seconds,
        latencies_ms=tuple(result.latency_ms for result in results),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a LearnMate HTTP baseline load test")
    parser.add_argument("--base-url", required=True, help="API origin, for example http://localhost:8000")
    parser.add_argument("--endpoint", default="/health/live", help="GET endpoint to exercise")
    parser.add_argument("--requests", type=int, default=100, dest="total_requests")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5.0, dest="timeout_seconds")
    parser.add_argument("--bearer-token", help="Optional token for an authenticated endpoint")
    args = parser.parse_args()

    summary = run_load(
        args.base_url,
        args.endpoint,
        args.total_requests,
        args.concurrency,
        args.timeout_seconds,
        args.bearer_token,
    )
    print(f"requests={summary.total_requests}")
    print(f"successful={summary.successful_requests} failed={summary.failed_requests}")
    print(f"error_rate={summary.error_rate:.2%}")
    print(f"throughput_rps={summary.throughput_per_second:.2f}")
    print(f"p50_ms={summary.percentile_ms(50):.2f}")
    print(f"p95_ms={summary.percentile_ms(95):.2f}")
    print(f"p99_ms={summary.percentile_ms(99):.2f}")
    return 0 if summary.failed_requests == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
