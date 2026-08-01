from types import SimpleNamespace

from app.rate_limit import RequestRateLimiter


def _request(path: str, *, authorization: str | None = None):
    headers = {"authorization": authorization} if authorization else {}
    return SimpleNamespace(
        method="POST",
        url=SimpleNamespace(path=path),
        headers=headers,
        client=SimpleNamespace(host="127.0.0.1"),
    )


def test_rate_limiter_blocks_only_after_route_limit():
    limiter = RequestRateLimiter(window_seconds=60)
    request = _request("/api/v1/auth/login")
    for _ in range(10):
        assert limiter.check(request)[0] is True
    allowed, retry_after = limiter.check(request)
    assert allowed is False
    assert retry_after >= 1
    assert limiter.check(_request("/health"))[0] is True


def test_rate_limiter_separates_authenticated_identities():
    limiter = RequestRateLimiter(window_seconds=60)
    first = _request("/api/v1/auth/login", authorization="Bearer first")
    second = _request("/api/v1/auth/login", authorization="Bearer second")
    for _ in range(10):
        assert limiter.check(first)[0] is True
    assert limiter.check(first)[0] is False
    assert limiter.check(second)[0] is True
