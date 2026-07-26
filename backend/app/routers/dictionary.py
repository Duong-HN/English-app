"""Authenticated word-detail lookup with independent provider caches."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..external_dict import (
    ExternalDictionaryClient,
    get_external_dictionary_client,
    normalize_word,
)
from ..models import User, WordLookupCache, utc_now
from ..schemas import WordLookupResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])

DICTIONARY_CACHE_TTL = timedelta(days=30)
DATAMUSE_CACHE_TTL = timedelta(days=7)


def _as_utc(value: datetime) -> datetime:
    # SQLite drops timezone information even for DateTime(timezone=True).
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_fresh(
    cached_at: datetime | None,
    ttl: timedelta,
    now: datetime,
) -> bool:
    return cached_at is not None and _as_utc(cached_at) >= now - ttl


def _build_response(
    word: str,
    dictionary_payload: dict | None,
    datamuse_payload: dict | None,
    *,
    cached: bool,
) -> WordLookupResponse:
    dictionary_data = dictionary_payload if isinstance(dictionary_payload, dict) else {}
    datamuse_data = datamuse_payload if isinstance(datamuse_payload, dict) else {}
    try:
        return WordLookupResponse.model_validate(
            {
                "word": word,
                "phonetics": dictionary_data.get("phonetics", []),
                "meanings": dictionary_data.get("meanings", []),
                "synonyms": datamuse_data.get("synonyms", []),
                "antonyms": datamuse_data.get("antonyms", []),
                "collocations": datamuse_data.get("collocations", []),
                "cached": cached,
            }
        )
    except ValidationError:
        # A legacy/corrupted cache row should not make the vocabulary flow fail.
        logger.warning("Ignoring invalid cached dictionary payload for %r", word)
        return WordLookupResponse(word=word, cached=cached)


@router.get("/lookup/{word}", response_model=WordLookupResponse)
async def lookup_word(
    word: str = Path(min_length=1, max_length=120),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    external_client: ExternalDictionaryClient = Depends(get_external_dictionary_client),
) -> WordLookupResponse:
    try:
        normalized = normalize_word(word)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    now = utc_now()
    cache = db.get(WordLookupCache, normalized)
    dictionary_fresh = cache is not None and _is_fresh(
        cache.dict_cached_at,
        DICTIONARY_CACHE_TTL,
        now,
    )
    datamuse_fresh = cache is not None and _is_fresh(
        cache.datamuse_cached_at,
        DATAMUSE_CACHE_TTL,
        now,
    )

    dictionary_payload = cache.dictionary if cache is not None else None
    datamuse_payload = cache.datamuse if cache is not None else None
    calls = []
    sources: list[str] = []
    if not dictionary_fresh:
        calls.append(external_client.fetch_dictionary(normalized))
        sources.append("dictionary")
    if not datamuse_fresh:
        calls.append(external_client.fetch_datamuse(normalized))
        sources.append("datamuse")

    changed = False
    if calls:
        results = await asyncio.gather(*calls, return_exceptions=True)
        for source, result in zip(sources, results, strict=True):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                logger.warning("External %s lookup failed for %r: %s", source, normalized, result)
                continue
            if cache is None:
                cache = WordLookupCache(word=normalized)
            if source == "dictionary":
                cache.dictionary = result
                cache.dict_cached_at = now
                dictionary_payload = result
            else:
                cache.datamuse = result
                cache.datamuse_cached_at = now
                datamuse_payload = result
            changed = True

    if changed and cache is not None:
        db.add(cache)
        try:
            db.commit()
        except SQLAlchemyError:
            # Cache persistence is an optimization; live validated data is still useful.
            db.rollback()
            logger.exception("Could not persist dictionary cache for %r", normalized)

    return _build_response(
        normalized,
        dictionary_payload,
        datamuse_payload,
        cached=dictionary_fresh and datamuse_fresh,
    )
