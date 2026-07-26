from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.external_dict import ExternalDictionaryClient, ExternalDictionaryError
from app.main import app
from app.models import WordLookupCache
from app.routers import dictionary as dictionary_router


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "safe-password-123",
            "display_name": "Dictionary Learner",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class FakeDictionaryClient:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.dictionary_calls = 0
        self.datamuse_calls = 0

    async def fetch_dictionary(self, word: str) -> dict | None:
        self.dictionary_calls += 1
        if self.fail:
            raise ExternalDictionaryError("dictionary timeout")
        return {
            "phonetics": [{"text": "/həˈləʊ/", "audio_url": "https://audio.example/hello.mp3"}],
            "meanings": [
                {
                    "part_of_speech": "exclamation",
                    "definitions": ["Used as a greeting."],
                    "examples": ["Hello, how are you?"],
                }
            ],
        }

    async def fetch_datamuse(self, word: str) -> dict:
        self.datamuse_calls += 1
        if self.fail:
            raise ExternalDictionaryError("datamuse timeout")
        return {
            "synonyms": ["greeting"],
            "antonyms": ["goodbye"],
            "collocations": ["say hello", "hello world"],
        }


def test_word_lookup_requires_authentication(client):
    response = client.get("/api/v1/vocabulary/lookup/hello")

    assert response.status_code == 401


def test_word_lookup_fetches_then_uses_cache(client, db_session):
    db_session.query(WordLookupCache).filter_by(word="hello").delete()
    db_session.commit()
    headers = _register(client, "dictionary-cache@example.com")
    fake = FakeDictionaryClient()
    app.dependency_overrides[dictionary_router.get_external_dictionary_client] = lambda: fake
    try:
        first = client.get("/api/v1/vocabulary/lookup/Hello", headers=headers)
        second = client.get("/api/v1/vocabulary/lookup/hello", headers=headers)
    finally:
        app.dependency_overrides.pop(dictionary_router.get_external_dictionary_client, None)

    assert first.status_code == 200, first.text
    assert first.json() == {
        "word": "hello",
        "phonetics": [{"text": "/həˈləʊ/", "audio_url": "https://audio.example/hello.mp3"}],
        "meanings": [
            {
                "part_of_speech": "exclamation",
                "definitions": ["Used as a greeting."],
                "examples": ["Hello, how are you?"],
            }
        ],
        "synonyms": ["greeting"],
        "antonyms": ["goodbye"],
        "collocations": ["say hello", "hello world"],
        "cached": False,
    }
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert fake.dictionary_calls == 1
    assert fake.datamuse_calls == 1


def test_word_lookup_uses_stale_payload_when_providers_fail(client, db_session):
    db_session.query(WordLookupCache).filter_by(word="resilient").delete()
    db_session.add(
        WordLookupCache(
            word="resilient",
            dictionary={
                "phonetics": [],
                "meanings": [
                    {
                        "part_of_speech": "adjective",
                        "definitions": ["Able to recover quickly."],
                        "examples": [],
                    }
                ],
            },
            datamuse={
                "synonyms": ["strong"],
                "antonyms": [],
                "collocations": ["highly resilient"],
            },
            # Naive timestamps exercise SQLite's timezone round-trip behavior.
            dict_cached_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=31),
            datamuse_cached_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8),
        )
    )
    db_session.commit()
    headers = _register(client, "dictionary-stale@example.com")
    fake = FakeDictionaryClient(fail=True)
    app.dependency_overrides[dictionary_router.get_external_dictionary_client] = lambda: fake
    try:
        response = client.get("/api/v1/vocabulary/lookup/resilient", headers=headers)
    finally:
        app.dependency_overrides.pop(dictionary_router.get_external_dictionary_client, None)

    assert response.status_code == 200, response.text
    assert response.json()["meanings"][0]["definitions"] == ["Able to recover quickly."]
    assert response.json()["synonyms"] == ["strong"]
    assert response.json()["cached"] is False
    assert fake.dictionary_calls == 1
    assert fake.datamuse_calls == 1


def test_word_lookup_refreshes_provider_ttls_independently(client, db_session):
    db_session.query(WordLookupCache).filter_by(word="independent").delete()
    db_session.add(
        WordLookupCache(
            word="independent",
            dictionary={
                "phonetics": [],
                "meanings": [
                    {
                        "part_of_speech": "adjective",
                        "definitions": ["Not controlled by another."],
                        "examples": [],
                    }
                ],
            },
            datamuse={"synonyms": ["old"], "antonyms": [], "collocations": []},
            dict_cached_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=10),
            datamuse_cached_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8),
        )
    )
    db_session.commit()
    headers = _register(client, "dictionary-independent-ttl@example.com")
    fake = FakeDictionaryClient()
    app.dependency_overrides[dictionary_router.get_external_dictionary_client] = lambda: fake
    try:
        response = client.get("/api/v1/vocabulary/lookup/independent", headers=headers)
    finally:
        app.dependency_overrides.pop(dictionary_router.get_external_dictionary_client, None)

    assert response.status_code == 200, response.text
    assert response.json()["meanings"][0]["definitions"] == ["Not controlled by another."]
    assert response.json()["synonyms"] == ["greeting"]
    assert response.json()["cached"] is False
    assert fake.dictionary_calls == 0
    assert fake.datamuse_calls == 1


def test_confirmed_dictionary_not_found_is_negative_cached(client, db_session):
    class NotFoundClient(FakeDictionaryClient):
        async def fetch_dictionary(self, word: str) -> None:
            self.dictionary_calls += 1
            return None

        async def fetch_datamuse(self, word: str) -> dict:
            self.datamuse_calls += 1
            return {"synonyms": [], "antonyms": [], "collocations": []}

    db_session.query(WordLookupCache).filter_by(word="unlistedword").delete()
    db_session.commit()
    headers = _register(client, "dictionary-negative-cache@example.com")
    fake = NotFoundClient()
    app.dependency_overrides[dictionary_router.get_external_dictionary_client] = lambda: fake
    try:
        first = client.get("/api/v1/vocabulary/lookup/unlistedword", headers=headers)
        second = client.get("/api/v1/vocabulary/lookup/unlistedword", headers=headers)
    finally:
        app.dependency_overrides.pop(dictionary_router.get_external_dictionary_client, None)

    assert first.status_code == 200
    assert first.json()["meanings"] == []
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert fake.dictionary_calls == 1
    assert fake.datamuse_calls == 1


def test_word_lookup_rejects_non_english_word_before_external_call(client):
    headers = _register(client, "dictionary-validation@example.com")
    fake = FakeDictionaryClient()
    app.dependency_overrides[dictionary_router.get_external_dictionary_client] = lambda: fake
    try:
        response = client.get("/api/v1/vocabulary/lookup/hello%20world", headers=headers)
    finally:
        app.dependency_overrides.pop(dictionary_router.get_external_dictionary_client, None)

    assert response.status_code == 422
    assert fake.dictionary_calls == 0
    assert fake.datamuse_calls == 0


@pytest.mark.asyncio
async def test_external_adapter_validates_and_builds_full_collocations():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.dictionaryapi.dev":
            return httpx.Response(
                200,
                json=[
                    {
                        "phonetic": "/həˈləʊ/",
                        "phonetics": [
                            {"text": "/həˈləʊ/", "audio": "//audio.example/hello.mp3"},
                            {"audio": "http://insecure.example/hello.mp3"},
                        ],
                        "meanings": [
                            {
                                "partOfSpeech": "exclamation",
                                "definitions": [
                                    {
                                        "definition": "Used as a greeting.",
                                        "example": "Hello there!",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            )
        relation = next(key for key in request.url.params if key.startswith("rel_"))
        words = {
            "rel_syn": ["hi"],
            "rel_ant": ["goodbye"],
            "rel_bga": ["world"],
            "rel_bgb": ["say"],
        }[relation]
        return httpx.Response(200, json=[{"word": word} for word in words])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        adapter = ExternalDictionaryClient(http_client)
        dictionary_payload = await adapter.fetch_dictionary("HELLO")
        datamuse_payload = await adapter.fetch_datamuse("hello")

    assert dictionary_payload is not None
    assert dictionary_payload["phonetics"] == [
        {"text": "/həˈləʊ/", "audio_url": "https://audio.example/hello.mp3"}
    ]
    assert datamuse_payload == {
        "synonyms": ["hi"],
        "antonyms": ["goodbye"],
        "collocations": ["say hello", "hello world"],
    }


@pytest.mark.asyncio
async def test_external_adapter_distinguishes_not_found_from_outage():
    def not_found_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"title": "No Definitions Found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(not_found_handler)) as http_client:
        assert await ExternalDictionaryClient(http_client).fetch_dictionary("unknownword") is None

    def outage_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(outage_handler)) as http_client:
        with pytest.raises(ExternalDictionaryError, match="unavailable"):
            await ExternalDictionaryClient(http_client).fetch_dictionary("hello")
