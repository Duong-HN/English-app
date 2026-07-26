"""Validated adapters for the external dictionary services.

Only the normalized English word is sent to dictionaryapi.dev and Datamuse.
Transport failures are raised to the caller so they are never confused with a
confirmed Dictionary API 404 and never overwrite a usable stale cache entry.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator, Iterable

import httpx

logger = logging.getLogger(__name__)

DICTIONARY_BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"
DATAMUSE_URL = "https://api.datamuse.com/words"
DEFAULT_TIMEOUT_SECONDS = 5.0

_WORD_RE = re.compile(r"^[a-z](?:[a-z'-]{0,118}[a-z])?$")


class ExternalDictionaryError(RuntimeError):
    """The external provider did not return a usable response."""


def normalize_word(word: str) -> str:
    """Return the canonical cache key or reject unsupported input."""
    normalized = word.strip().lower()
    if not _WORD_RE.fullmatch(normalized):
        raise ValueError("word must contain only English letters, apostrophes, or hyphens")
    return normalized


def _clean_text(value: object, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    return cleaned[:max_length]


def _unique_strings(
    values: Iterable[object],
    *,
    max_items: int,
    max_length: int,
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value, max_length=max_length)
        if cleaned is None or cleaned.casefold() in seen:
            continue
        result.append(cleaned)
        seen.add(cleaned.casefold())
        if len(result) == max_items:
            break
    return result


def _normalize_audio(value: object) -> str | None:
    url = _clean_text(value, max_length=2048)
    if url is None:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("https://"):
        return url
    # The mobile client must not be handed insecure or non-HTTP media URLs.
    return None


def _parse_dictionary_payload(payload: object) -> dict:
    if not isinstance(payload, list) or not payload:
        raise ExternalDictionaryError("Dictionary API returned an invalid document")
    entry = next((item for item in payload if isinstance(item, dict)), None)
    if entry is None:
        raise ExternalDictionaryError("Dictionary API returned no valid entry")

    phonetics: list[dict[str, str | None]] = []
    raw_phonetics = entry.get("phonetics", [])
    if isinstance(raw_phonetics, list):
        for raw_phonetic in raw_phonetics[:12]:
            if not isinstance(raw_phonetic, dict):
                continue
            text = _clean_text(raw_phonetic.get("text"), max_length=120)
            audio_url = _normalize_audio(raw_phonetic.get("audio"))
            if text is not None or audio_url is not None:
                phonetics.append({"text": text, "audio_url": audio_url})
            if len(phonetics) == 8:
                break

    top_level_phonetic = _clean_text(entry.get("phonetic"), max_length=120)
    if not phonetics and top_level_phonetic is not None:
        phonetics.append({"text": top_level_phonetic, "audio_url": None})

    meanings: list[dict[str, object]] = []
    raw_meanings = entry.get("meanings", [])
    if isinstance(raw_meanings, list):
        for raw_meaning in raw_meanings[:12]:
            if not isinstance(raw_meaning, dict):
                continue
            definitions: list[object] = []
            examples: list[object] = []
            raw_definitions = raw_meaning.get("definitions", [])
            if isinstance(raw_definitions, list):
                for raw_definition in raw_definitions[:8]:
                    if not isinstance(raw_definition, dict):
                        continue
                    definitions.append(raw_definition.get("definition"))
                    examples.append(raw_definition.get("example"))
            part_of_speech = _clean_text(raw_meaning.get("partOfSpeech"), max_length=80) or ""
            cleaned_definitions = _unique_strings(
                definitions,
                max_items=5,
                max_length=2000,
            )
            cleaned_examples = _unique_strings(examples, max_items=5, max_length=2000)
            if part_of_speech or cleaned_definitions or cleaned_examples:
                meanings.append(
                    {
                        "part_of_speech": part_of_speech,
                        "definitions": cleaned_definitions,
                        "examples": cleaned_examples,
                    }
                )

    return {"phonetics": phonetics, "meanings": meanings}


def _parse_word_list(payload: object) -> list[str]:
    if not isinstance(payload, list):
        raise ExternalDictionaryError("Datamuse returned an invalid document")
    values = [item.get("word") for item in payload if isinstance(item, dict)]
    return _unique_strings(values, max_items=8, max_length=120)


class ExternalDictionaryClient:
    """HTTP adapter whose client can be replaced by ``httpx.MockTransport`` in tests."""

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def fetch_dictionary(self, word: str) -> dict | None:
        """Fetch a dictionary entry; ``None`` means a confirmed upstream 404."""
        normalized = normalize_word(word)
        try:
            response = await self.client.get(f"{DICTIONARY_BASE_URL}/{normalized}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalDictionaryError("Dictionary API is unavailable") from exc
        return _parse_dictionary_payload(payload)

    async def fetch_datamuse(self, word: str) -> dict:
        """Fetch synonyms, antonyms and full predecessor/follower phrases."""
        normalized = normalize_word(word)

        async def get_words(params: dict[str, str | int]) -> list[str]:
            try:
                response = await self.client.get(DATAMUSE_URL, params=params)
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise ExternalDictionaryError("Datamuse is unavailable") from exc
            return _parse_word_list(payload)

        synonyms, antonyms, followers, predecessors = await asyncio.gather(
            get_words({"rel_syn": normalized, "max": 8}),
            get_words({"rel_ant": normalized, "max": 8}),
            get_words({"rel_bga": normalized, "max": 8}),
            get_words({"rel_bgb": normalized, "max": 8}),
        )
        collocations = _unique_strings(
            [
                *(f"{candidate} {normalized}" for candidate in predecessors[:4]),
                *(f"{normalized} {candidate}" for candidate in followers[:4]),
            ],
            max_items=8,
            max_length=241,
        )
        return {
            "synonyms": synonyms,
            "antonyms": antonyms,
            "collocations": collocations,
        }


async def get_external_dictionary_client() -> AsyncIterator[ExternalDictionaryClient]:
    """FastAPI dependency providing one pooled client for a lookup request."""
    timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        yield ExternalDictionaryClient(client)


async def fetch_dictionary(word: str) -> dict | None:
    """Backward-compatible graceful helper for non-request callers."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        try:
            return await ExternalDictionaryClient(client).fetch_dictionary(word)
        except (ExternalDictionaryError, ValueError) as exc:
            logger.warning("Dictionary lookup failed for %r: %s", word, exc)
            return None


async def fetch_datamuse(word: str) -> dict:
    """Backward-compatible graceful helper for non-request callers."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
        try:
            return await ExternalDictionaryClient(client).fetch_datamuse(word)
        except (ExternalDictionaryError, ValueError) as exc:
            logger.warning("Datamuse lookup failed for %r: %s", word, exc)
            return {"synonyms": [], "antonyms": [], "collocations": []}
