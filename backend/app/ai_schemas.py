from pydantic import BaseModel, Field, model_validator


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


class DailyLearningTask(BaseModel):
    day: int = Field(ge=1, le=7)
    title: str
    skill: str
    activity: str
    duration_minutes: int = Field(ge=10, le=120)
    success_criteria: str


class LearningPathResult(BaseModel):
    summary: str
    weekly_goal: str
    focus_areas: list[str] = Field(min_length=1, max_length=5)
    personalization_notes: list[str] = Field(default_factory=list, max_length=5)
    daily_tasks: list[DailyLearningTask] = Field(min_length=7, max_length=7)
    checkpoints: list[str] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def require_sequential_days(self):
        days = [task.day for task in self.daily_tasks]
        if days != list(range(1, 8)):
            raise ValueError("daily_tasks must contain days 1 through 7 in order")
        return self


RESULT_MODELS = {
    "reading": ReadingResult,
    "writing": WritingResult,
    "speaking": SpeakingResult,
}


def validate_ai_result(analysis_type: str, result: dict) -> dict:
    model = RESULT_MODELS[analysis_type]
    return model.model_validate(result).model_dump()
