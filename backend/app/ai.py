import json
from typing import Protocol

import httpx

from .config import Settings


class AiProvider(Protocol):
    name: str

    async def analyze(self, analysis_type: str, input_text: str) -> dict: ...


class MockAiProvider:
    name = "mock"

    async def analyze(self, analysis_type: str, input_text: str) -> dict:
        if analysis_type == "reading":
            return {
                "summary": "Đoạn văn nói về một hành động đơn giản trong đời sống.",
                "translation": "Đây là bản dịch minh họa cho MVP.",
                "vocabulary": [
                    {"word": "quick", "meaning": "nhanh", "example": "a quick response"},
                    {"word": "jumps", "meaning": "nhảy qua", "example": "The dog jumps."},
                ],
                "issues": [],
                "questions": [
                    {"question": "What is the main action?", "answer": "The subject jumps."}
                ],
            }
        if analysis_type == "writing":
            return {
                "score": 7.5,
                "summary": "Bài viết có ý rõ ràng. Hãy bổ sung liên từ và kiểm tra thì động từ.",
                "issues": [
                    {"title": "Mẫu nhận xét", "explanation": "Đây là nhận xét từ Mock AI để kiểm thử luồng ứng dụng."}
                ],
                "rewrite": input_text,
            }
        return {
            "score": 7.0,
            "summary": "Câu trả lời có thể hiểu được và bám chủ đề.",
            "issues": [
                {"title": "Đánh giá nội dung", "explanation": "MVP đang đánh giá transcript, chưa phải điểm phát âm chuẩn."}
            ],
            "pronunciation_note": "Chức năng phát âm sẽ nhận audio từ các từ khóa mục tiêu ở phase tiếp theo.",
        }


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model

    async def analyze(self, analysis_type: str, input_text: str) -> dict:
        prompt = self._prompt(analysis_type, input_text)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
            )
            response.raise_for_status()
            payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

    def _prompt(self, analysis_type: str, input_text: str) -> str:
        instructions = {
            "reading": "Return summary, Vietnamese translation, 3 vocabulary items, and 3 comprehension questions.",
            "writing": "Return a formative score from 0 to 10, summary, issues with explanations, and a rewrite.",
            "speaking": "Evaluate only content, grammar and vocabulary of this transcript. Do not claim to assess pronunciation from text. Return a formative score from 0 to 10 and feedback.",
        }[analysis_type]
        return f"""You are a supportive English teacher. {instructions}
Return valid JSON only. Input:
{input_text}"""


def build_provider(settings: Settings) -> AiProvider:
    if settings.ai_provider.lower() == "gemini":
        return GeminiProvider(settings)
    return MockAiProvider()
