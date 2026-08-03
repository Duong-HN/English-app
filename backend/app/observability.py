"""Low-cardinality request metrics and safe structured request logging."""

import json
import logging
import threading
import time
from collections import defaultdict
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("learnmate.request")


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, int], int] = defaultdict(int)
        self._duration_seconds: dict[tuple[str, str], float] = defaultdict(float)
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

    def observe_request(self, method: str, route: str, status_code: int, duration_seconds: float) -> None:
        key = (method, route, status_code)
        duration_key = (method, route)
        with self._lock:
            self._requests[key] += 1
            self._duration_seconds[duration_key] += duration_seconds

    def render_prometheus(self) -> str:
        lines = [
            "# HELP learnmate_http_requests_total Total HTTP requests by method, route and status.",
            "# TYPE learnmate_http_requests_total counter",
        ]
        with self._lock:
            for (method, route, status_code), count in sorted(self._requests.items()):
                labels = f'method="{method}",route="{route}",status="{status_code}"'
                lines.append(f"learnmate_http_requests_total{{{labels}}} {count}")
            lines.extend(
                [
                    "# HELP learnmate_http_request_duration_seconds_sum Total request duration in seconds.",
                    "# TYPE learnmate_http_request_duration_seconds_sum counter",
                ]
            )
            for (method, route), duration in sorted(self._duration_seconds.items()):
                labels = f'method="{method}",route="{route}"'
                lines.append(f"learnmate_http_request_duration_seconds_sum{{{labels}}} {duration:.6f}")
            for (name, label_items), value in sorted(self._gauges.items()):
                labels = ",".join(f'{key}="{label_value}"' for key, label_value in label_items)
                lines.append(f"{name}{{{labels}}} {value}")
        return "\n".join(lines) + "\n"

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        label_items = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._gauges[(name, label_items)] = value


metrics = MetricsRegistry()


def request_id(request: Request) -> str:
    candidate = request.headers.get("X-Request-ID", "").strip()
    if candidate and len(candidate) <= 128 and all(char.isalnum() or char in "-_.:" for char in candidate):
        return candidate
    return str(uuid4())


def route_template(request: Request) -> str:
    route = request.scope.get("route")
    return str(getattr(route, "path", request.url.path))


def log_request(request: Request, request_id_value: str, status_code: int, duration_seconds: float) -> None:
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id_value,
                "method": request.method,
                "route": route_template(request),
                "status": status_code,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
            separators=(",", ":"),
        )
    )


def monotonic_seconds() -> float:
    return time.perf_counter()
