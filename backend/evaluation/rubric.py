from __future__ import annotations

from collections.abc import Iterable, Mapping
from statistics import mean
from typing import Any

RATING_FIELDS = ("correctness", "usefulness", "level_fit", "grounding")
REQUIRED_REVIEW_FIELDS = ("case_id", "reviewer_id", *RATING_FIELDS, "hallucination")


def validate_review(review: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_REVIEW_FIELDS if field not in review]
    if missing:
        raise ValueError(f"Missing review fields: {', '.join(missing)}")

    normalized = dict(review)
    for field in RATING_FIELDS:
        value = normalized[field]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"{field} must be an integer from 1 to 5")

    if not isinstance(normalized["hallucination"], bool):
        raise ValueError("hallucination must be a boolean")
    if not str(normalized["case_id"]).strip():
        raise ValueError("case_id must not be empty")
    if not str(normalized["reviewer_id"]).strip():
        raise ValueError("reviewer_id must not be empty")
    return normalized


def summarize_reviews(reviews: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    validated = [validate_review(review) for review in reviews]
    if not validated:
        return {
            "reviewed_samples": 0,
            "average_scores": {field: None for field in RATING_FIELDS},
            "hallucination_rate": None,
            "meets_minimum_sample": False,
            "status": "pending",
        }

    averages = {field: round(mean(review[field] for review in validated), 2) for field in RATING_FIELDS}
    hallucination_rate = round(
        sum(review["hallucination"] for review in validated) / len(validated),
        4,
    )
    return {
        "reviewed_samples": len(validated),
        "average_scores": averages,
        "hallucination_rate": hallucination_rate,
        "meets_minimum_sample": len(validated) >= 30,
        "status": "complete" if len(validated) >= 30 else "insufficient_sample",
    }
