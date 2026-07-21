import json

import httpx
import pytest
from pydantic import ValidationError

from app.ai import GeminiProvider, MockAiProvider
from app.ai_schemas import LearningPathResult
from app.config import Settings


def test_speaking_prompt_explicitly_excludes_pronunciation_scoring():
    prompt = GeminiProvider._prompt("speaking", "I enjoy learning English.")

    assert "Do not claim to assess pronunciation" in prompt
    assert "relevance, grammar and vocabulary" in prompt


@pytest.mark.asyncio
async def test_mock_learning_path_avoids_acoustic_claims_and_has_sequential_days():
    result = await MockAiProvider().generate_learning_path(
        {"goal": "Speak confidently", "current_level": "B1", "minutes_per_day": 30},
        {"recommended_focus": "speaking", "analysis_counts": {"speaking": 2}},
    )

    assert [task["day"] for task in result["daily_tasks"]] == list(range(1, 8))
    serialized = json.dumps(result, ensure_ascii=False).lower()
    assert "khoảng dừng" not in serialized
    assert "chấm phát âm" not in serialized


@pytest.mark.asyncio
async def test_learning_path_schema_rejects_duplicate_or_out_of_order_days():
    result = await MockAiProvider().generate_learning_path(
        {"goal": "Improve writing", "current_level": "A2", "minutes_per_day": 20},
        {"recommended_focus": "writing", "analysis_counts": {}},
    )
    result["daily_tasks"][1]["day"] = 1

    with pytest.raises(ValidationError, match="days 1 through 7"):
        LearningPathResult.model_validate(result)


@pytest.mark.asyncio
async def test_gemini_uses_json_schema_and_validates_response():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.headers["x-goog-api-key"] == "test-gemini-key"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "score": 8.0,
                                            "summary": "Clear writing.",
                                            "issues": [],
                                            "rewrite": "I practise English every day.",
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    settings = Settings(
        ai_provider="gemini",
        gemini_api_key="test-gemini-key",
        gemini_model="gemini-2.5-flash",
    )
    provider = GeminiProvider(settings, transport=httpx.MockTransport(handler))

    result = await provider.analyze("writing", "I practice English every day.")

    generation_config = captured["generationConfig"]
    assert "responseJsonSchema" in generation_config
    assert "responseSchema" not in generation_config
    assert generation_config["responseJsonSchema"]["type"] == "object"
    assert result["score"] == 8.0


@pytest.mark.asyncio
async def test_gemini_learning_path_uses_recent_activity_and_structured_schema():
    captured: dict = {}
    tasks = [
        {
            "day": day,
            "title": f"Day {day}",
            "skill": "writing",
            "activity": "Write and revise a short paragraph.",
            "duration_minutes": 30,
            "success_criteria": "Complete one revised paragraph.",
        }
        for day in range(1, 8)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "summary": "A practical plan.",
                                            "weekly_goal": "Study every day.",
                                            "focus_areas": ["writing"],
                                            "personalization_notes": ["Writing has the lowest recent score."],
                                            "daily_tasks": tasks,
                                            "checkpoints": ["Compare day 1 and day 7."],
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    provider = GeminiProvider(
        Settings(ai_provider="gemini", gemini_api_key="test-gemini-key"),
        transport=httpx.MockTransport(handler),
    )
    result = await provider.generate_learning_path(
        {"goal": "Improve writing", "current_level": "B1", "minutes_per_day": 30},
        {"analysis_counts": {"writing": 3}, "average_scores": {"writing": 5.5}},
    )

    assert len(result["daily_tasks"]) == 7
    assert captured["generationConfig"]["responseJsonSchema"]["type"] == "object"
    prompt = captured["contents"][0]["parts"][0]["text"]
    assert "average_scores" in prompt
    assert "exactly seven daily tasks" in prompt
    assert "untrusted learner data" in prompt
