from pydantic import BaseModel, Field


class FeedbackIssue(BaseModel):
    title: str
    explanation: str


class VocabularyItem(BaseModel):
    word: str
    meaning: str
    example: str | None = None


class ComprehensionQuestion(BaseModel):
    question: str
    answer: str


class ReadingResult(BaseModel):
    summary: str
    translation: str
    vocabulary: list[VocabularyItem] = Field(default_factory=list)
    issues: list[FeedbackIssue] = Field(default_factory=list)
    questions: list[ComprehensionQuestion] = Field(default_factory=list)


class WritingResult(BaseModel):
    score: float = Field(ge=0, le=10)
    summary: str
    issues: list[FeedbackIssue] = Field(default_factory=list)
    rewrite: str


class SpeakingResult(BaseModel):
    score: float = Field(ge=0, le=10)
    summary: str
    issues: list[FeedbackIssue] = Field(default_factory=list)
    pronunciation_note: str


RESULT_MODELS = {
    "reading": ReadingResult,
    "writing": WritingResult,
    "speaking": SpeakingResult,
}


def validate_ai_result(analysis_type: str, result: dict) -> dict:
    model = RESULT_MODELS[analysis_type]
    return model.model_validate(result).model_dump()
