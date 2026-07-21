import json
from typing import Protocol

import httpx

from .ai_schemas import RESULT_MODELS, validate_ai_result
from .config import Settings


class AiProvider(Protocol):
    name: str

    async def analyze(self, analysis_type: str, input_text: str) -> dict: ...


class MockAiProvider:
    name = "mock"

    async def analyze(self, analysis_type: str, input_text: str) -> dict:
        if analysis_type == "reading":
            result = {
                "summary": "Đoạn văn trình bày một ý hoặc hành động bằng tiếng Anh.",
                "translation": f"Bản dịch minh họa cho: {input_text}",
                "vocabulary": [
                    {"word": "practice", "meaning": "luyện tập", "example": "Practice every day."},
                    {"word": "improve", "meaning": "cải thiện", "example": "Reading improves vocabulary."},
                ],
                "issues": [],
                "questions": [
                    {"question": "What is the main idea?", "answer": "The main idea is stated in the text."}
                ],
            }
        elif analysis_type == "writing":
            result = {
                "score": 7.5,
                "summary": "Bài viết có ý rõ ràng. Hãy bổ sung liên từ và kiểm tra thì động từ.",
                "issues": [
                    {
                        "title": "Mẫu nhận xét",
                        "explanation": "Đây là phản hồi xác định từ Mock AI dùng cho kiểm thử.",
                    }
                ],
                "rewrite": input_text,
            }
        else:
            result = {
                "score": 7.0,
                "summary": "Câu trả lời có thể hiểu được và bám chủ đề.",
                "issues": [
                    {
                        "title": "Đánh giá transcript",
                        "explanation": "Điểm chỉ phản ánh nội dung, ngữ pháp và từ vựng của transcript.",
                    }
                ],
                "pronunciation_note": (
                    "Không suy luận điểm phát âm từ văn bản. Cần audio và bộ đánh giá riêng."
                ),
            }
        return validate_ai_result(analysis_type, result)


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.timeout = settings.ai_timeout_seconds
        self.transport = transport

    async def analyze(self, analysis_type: str, input_text: str) -> dict:
        prompt = self._prompt(analysis_type, input_text)
        schema = RESULT_MODELS[analysis_type].model_json_schema()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "responseJsonSchema": schema,
                        "temperature": 0.2,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return validate_ai_result(analysis_type, json.loads(text))

    @staticmethod
    def _prompt(analysis_type: str, input_text: str) -> str:
        instructions = {
            "reading": (
                "Explain the main idea in Vietnamese, translate naturally, select useful vocabulary, "
                "and create comprehension questions."
            ),
            "writing": (
                "Give formative feedback from 0 to 10 for grammar, vocabulary, coherence and task response. "
                "Explain concrete issues and provide a natural rewrite. Do not claim an official IELTS score."
            ),
            "speaking": (
                "Evaluate only relevance, grammar and vocabulary in this speech transcript. "
                "Do not claim to assess pronunciation or accent from text."
            ),
        }[analysis_type]
        return (
            "You are a supportive English teacher for Vietnamese learners. "
            f"{instructions}\nLearner input:\n{input_text}"
        )


def build_provider(settings: Settings) -> AiProvider:
    if settings.ai_provider.lower() == "gemini":
        return GeminiProvider(settings)
    if settings.ai_provider.lower() == "mock":
        return MockAiProvider()
    raise ValueError(f"Unsupported AI_PROVIDER: {settings.ai_provider}")
