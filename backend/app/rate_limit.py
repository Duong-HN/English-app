"""Small in-process abuse guard for the prototype API.

This is intentionally not presented as a distributed production limiter. Every
API replica needs the same decision from a gateway or Redis-backed store before
public launch.
"""

import hashlib
import threading
import time
from collections import defaultdict, deque
from math import ceil
from typing import Protocol


class RequestLike(Protocol):
    method: str
    url: object
    headers: object
    client: object


RULES: tuple[tuple[str, str, int], ...] = (
    ("POST", "/api/v1/auth/login", 10),
    ("POST", "/api/v1/auth/register", 5),
    ("POST", "/api/v1/analysis-jobs/", 20),
    ("POST", "/api/v1/analyses/", 20),
    ("POST", "/api/v1/learning-paths", 10),
)


class RequestRateLimiter:
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, request: RequestLike) -> tuple[bool, int]:
        rule = next(
            (
                (limit, prefix)
                for method, prefix, limit in RULES
                if request.method == method and request.url.path.startswith(prefix)
            ),
            None,
        )
        if rule is None:
            return True, 0
        limit, prefix = rule
        key = (prefix, self._identity(request))
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, ceil(self.window_seconds - (now - bucket[0])))
                return False, retry_after
            bucket.append(now)
            if len(self._buckets) > 10_000:
                self._buckets = defaultdict(
                    deque,
                    {item_key: values for item_key, values in self._buckets.items() if values},
                )
        return True, 0

    @staticmethod
    def _identity(request: RequestLike) -> str:
        authorization = request.headers.get("authorization")
        if authorization:
            return "token:" + hashlib.sha256(authorization.encode()).hexdigest()
        host = request.client.host if request.client else "unknown"
        return f"ip:{host}"


class RedisRateLimiter:
    """Atomic sliding-window limiter for deployments with multiple API replicas."""

    _script = """
    local now = tonumber(ARGV[1])
    local cutoff = now - tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, cutoff)
    local count = redis.call('ZCARD', KEYS[1])
    if count >= limit then
        redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
        return {0, tonumber(ARGV[2])}
    end
    redis.call('ZADD', KEYS[1], now, ARGV[4])
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
    return {1, 0}
    """

    def __init__(self, redis_url: str, window_seconds: int = 60):
        try:
            from redis import Redis
        except ImportError as exc:
            raise RuntimeError("redis package is required when RATE_LIMIT_BACKEND=redis") from exc
        self.client = Redis.from_url(redis_url, decode_responses=True)
        self.window_seconds = window_seconds

    def check(self, request: RequestLike) -> tuple[bool, int]:
        rule = next(
            (
                (limit, prefix)
                for method, prefix, limit in RULES
                if request.method == method and request.url.path.startswith(prefix)
            ),
            None,
        )
        if rule is None:
            return True, 0
        limit, prefix = rule
        now = time.time()
        identity = RequestRateLimiter._identity(request)
        key = f"learnmate:rate:{prefix}:{identity}"
        result = self.client.eval(
            self._script, 1, key, now, self.window_seconds, limit, f"{now}:{secrets_token()}"
        )
        return bool(result[0]), int(result[1])


def secrets_token() -> str:
    return hashlib.sha256(f"{time.time_ns()}".encode()).hexdigest()
