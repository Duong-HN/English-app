import json

import httpx
import pytest

from app.ai import GeminiProvider
from app.config import Settings


def test_speaking_prompt_explicitly_excludes_pronunciation_scoring():
    prompt = GeminiProvider._prompt("speaking", "I enjoy learning English.")

    assert "Do not claim to assess pronunciation" in prompt
    assert "relevance, grammar and vocabulary" in prompt


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
