import json
from pathlib import Path

import pytest

from app.ai_schemas import RESULT_MODELS
from evaluation.rubric import summarize_reviews, validate_review

CASES_PATH = Path(__file__).parents[1] / "evaluation" / "ai_cases.jsonl"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_ai_evaluation_manifest_has_representative_cases():
    cases = load_cases()

    assert len(cases) >= 30
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["type"] for case in cases} == set(RESULT_MODELS)
    assert {case["level"] for case in cases} >= {"A2", "B1", "B2", "C1"}
    assert all(case["input_text"] is not None for case in cases)
    assert all(case["expected_focus"] for case in cases)


def test_ai_evaluation_manifest_contains_empty_input_case():
    assert any(case["input_text"] == "" for case in load_cases())


def test_rubric_requires_complete_human_review():
    with pytest.raises(ValueError, match="Missing review fields"):
        validate_review({"case_id": "writing-01", "reviewer_id": "teacher-1"})


def test_rubric_rejects_invalid_ratings():
    review = {
        "case_id": "writing-01",
        "reviewer_id": "teacher-1",
        "correctness": 6,
        "usefulness": 4,
        "level_fit": 4,
        "grounding": 4,
        "hallucination": False,
    }

    with pytest.raises(ValueError, match="correctness"):
        validate_review(review)


def test_rubric_returns_pending_without_human_reviews():
    result = summarize_reviews([])

    assert result["status"] == "pending"
    assert result["reviewed_samples"] == 0
    assert result["meets_minimum_sample"] is False


def test_rubric_summarizes_reviews_without_fabricating_completion():
    reviews = [
        {
            "case_id": "writing-01",
            "reviewer_id": "teacher-1",
            "correctness": 5,
            "usefulness": 4,
            "level_fit": 4,
            "grounding": 5,
            "hallucination": False,
        },
        {
            "case_id": "writing-02",
            "reviewer_id": "teacher-1",
            "correctness": 3,
            "usefulness": 3,
            "level_fit": 4,
            "grounding": 3,
            "hallucination": True,
        },
    ]

    result = summarize_reviews(reviews)

    assert result["reviewed_samples"] == 2
    assert result["average_scores"]["correctness"] == 4
    assert result["hallucination_rate"] == 0.5
    assert result["status"] == "insufficient_sample"
