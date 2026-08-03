from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .ai_schemas import LearningPathResult

AnalysisType = Literal["reading", "writing", "speaking"]
AnalysisJobStatus = Literal["queued", "processing", "succeeded", "failed"]
LearningPathJobOperation = Literal["generate", "adapt", "onboarding"]
MediaType = Literal["audio", "video"]
LearningLevel = Literal["A1", "A2", "B1", "B2", "C1"]
GoalCode = Literal["ielts", "communication", "study_abroad", "work"]
LearningSpaceKind = Literal["self", "class"]
OnboardingStatus = Literal[
    "needs_mode",
    "needs_goal",
    "needs_daily_time",
    "needs_placement",
    "needs_learning_path",
    "class_ready",
    "completed",
]
TeacherApplicationStatus = Literal["pending", "approved", "rejected"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("display_name must contain at least 2 non-whitespace characters")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    mfa_code: str | None = Field(default=None, pattern=r"^\d{6}$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    role: str
    level: str | None
    is_active: bool
    created_at: datetime


class TeacherApplicationCreate(BaseModel):
    motivation: str = Field(min_length=20, max_length=2000)
    organization: str | None = Field(default=None, max_length=160)

    @field_validator("motivation")
    @classmethod
    def clean_motivation(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 20:
            raise ValueError("motivation must contain at least 20 non-whitespace characters")
        return cleaned

    @field_validator("organization")
    @classmethod
    def clean_organization(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class TeacherApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    motivation: str
    organization: str | None
    status: TeacherApplicationStatus
    review_note: str | None
    requested_at: datetime
    reviewed_at: datetime | None


class TeacherApplicationStatusResponse(BaseModel):
    application: TeacherApplicationResponse | None


class TeacherApplicationReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=2000)

    @field_validator("review_note")
    @classmethod
    def clean_review_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class MfaCodeRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaStatusResponse(BaseModel):
    enabled: bool


class AnalysisRequest(BaseModel):
    input_text: str = Field(min_length=3, max_length=10000)
    learning_path_id: str | None = Field(default=None, max_length=64)
    task_day: int | None = Field(default=None, ge=1, le=7)
    lesson_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_task_context(self):
        if self.task_day is not None and self.learning_path_id is None:
            raise ValueError("learning_path_id is required when task_day is provided")
        return self

    @field_validator("input_text")
    @classmethod
    def clean_input(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("input_text must contain at least 3 non-whitespace characters")
        return value


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: AnalysisType
    input_text: str
    result: dict
    score: float | None
    provider: str
    lesson_id: str | None
    learning_path_id: str | None
    task_day: int | None
    created_at: datetime


class AiEvaluationReviewCreate(BaseModel):
    analysis_id: str = Field(min_length=1, max_length=64)
    case_id: str | None = Field(default=None, max_length=128)
    correctness: int = Field(ge=1, le=5)
    usefulness: int = Field(ge=1, le=5)
    level_fit: int = Field(ge=1, le=5)
    grounding: int = Field(ge=1, le=5)
    hallucination: int = Field(ge=1, le=5)
    reviewer_note: str | None = Field(default=None, max_length=4000)

    @field_validator("case_id", "reviewer_note")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class AiEvaluationReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    reviewer_id: str
    reviewer_email: EmailStr
    case_id: str | None
    correctness: int
    usefulness: int
    level_fit: int
    grounding: int
    hallucination: int
    reviewer_note: str | None
    created_at: datetime
    updated_at: datetime | None


class AiEvaluationReviewListResponse(BaseModel):
    items: list[AiEvaluationReviewResponse]
    total: int


class AiEvaluationSummaryResponse(BaseModel):
    review_count: int
    minimum_required: int
    status: Literal["pending", "insufficient_sample", "complete"]
    average_correctness: float | None
    average_usefulness: float | None
    average_level_fit: float | None
    average_grounding: float | None
    average_hallucination: float | None
    hallucination_rate: float | None


class AnalysisJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: AnalysisType
    status: AnalysisJobStatus
    analysis_id: str | None
    provider: str | None
    error_message: str | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime | None


class AssignmentGradingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    learner_id: str
    submission_id: str
    skill: AnalysisType
    status: AnalysisJobStatus
    analysis_id: str | None
    provider: str | None
    error_message: str | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime | None


class HistoryResponse(BaseModel):
    items: list[AnalysisResponse]
    total: int


class LearningPathGenerateRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=240)
    current_level: LearningLevel
    minutes_per_day: int = Field(ge=10, le=120)

    @field_validator("goal")
    @classmethod
    def clean_goal(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3:
            raise ValueError("goal must contain at least 3 non-whitespace characters")
        return cleaned


class LearningPathJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operation: LearningPathJobOperation
    status: AnalysisJobStatus
    learning_path_id: str | None
    provider: str | None
    error_message: str | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime | None


class DailyProgress(BaseModel):
    completed: bool = False
    completed_at: datetime | None = None
    analysis_id: str | None = None
    note: str | None = Field(default=None, max_length=1000)


class DailyProgressUpdate(BaseModel):
    completed: bool
    note: str | None = Field(default=None, max_length=1000)


class LearningPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    goal: str
    current_level: LearningLevel
    minutes_per_day: int
    plan: LearningPathResult
    daily_progress: dict[str, DailyProgress]
    level_source: Literal["placement", "self_reported"]
    placement_attempt_id: str | None
    provider: str
    created_at: datetime


class LearningPathListResponse(BaseModel):
    items: list[LearningPathResponse]
    total: int


class PlacementQuestionResponse(BaseModel):
    id: str
    prompt: str
    options: list[str]
    skill: Literal["grammar", "vocabulary", "reading"]


class PlacementTestResponse(BaseModel):
    questions: list[PlacementQuestionResponse]
    total_questions: int
    test_version: str


class PlacementSubmitRequest(BaseModel):
    answers: dict[str, str] = Field(min_length=20, max_length=20)

    @field_validator("answers")
    @classmethod
    def normalize_answers(cls, value: dict[str, str]) -> dict[str, str]:
        return {key.strip(): answer.strip().lower() for key, answer in value.items()}


class PlacementResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    score: int
    total_questions: int
    level: LearningLevel
    skill_scores: dict[str, dict[str, int | float]]
    test_version: str
    completed_at: datetime


class OnboardingPreferencesUpdate(BaseModel):
    goal: GoalCode | None = None
    daily_minutes: Literal[15, 20, 30, 45, 60] | None = None

    @model_validator(mode="after")
    def require_preference(self):
        provided = self.model_fields_set.intersection({"goal", "daily_minutes"})
        if not provided or any(getattr(self, field) is None for field in provided):
            raise ValueError("Provide a non-null goal and/or daily_minutes")
        return self


class LearningSpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: LearningSpaceKind
    class_id: str | None
    name: str
    goal: str | None
    daily_minutes: int | None
    current_level: LearningLevel | None
    course_code: str | None
    mode_selected_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class LearningSpaceListResponse(BaseModel):
    items: list[LearningSpaceResponse]
    total: int


class LearningSpaceModeUpdate(BaseModel):
    kind: Literal["self"]


class LearningSpaceJoinRequest(BaseModel):
    invite_code: str = Field(min_length=6, max_length=24)

    @field_validator("invite_code")
    @classmethod
    def normalize_invite_code(cls, value: str) -> str:
        return value.strip().upper()


class OnboardingResponse(BaseModel):
    status: OnboardingStatus
    space: LearningSpaceResponse
    available_spaces: list[LearningSpaceResponse]
    goal: str | None
    daily_minutes: int | None
    onboarding_completed_at: datetime | None
    updated_at: datetime | None
    placement_result: PlacementResultResponse | None
    learning_path: LearningPathResponse | None


class CourseLessonSummary(BaseModel):
    id: str
    lesson_number: int
    title: str
    skill: str
    content_type: str
    summary: str
    duration_minutes: int
    progress_status: str | None = None
    media_count: int = 0


class CourseUnitResponse(BaseModel):
    id: str
    unit_number: int
    title: str
    objective: str
    lessons: list[CourseLessonSummary]


class CourseResponse(BaseModel):
    id: str
    code: str
    title: str
    description: str
    kind: str
    level: LearningLevel | None
    band_min: float | None
    band_max: float | None
    units: list[CourseUnitResponse]


class CourseListResponse(BaseModel):
    items: list[CourseResponse]
    total: int


class LessonProgressUpdate(BaseModel):
    status: Literal["started", "completed"]
    score: float | None = Field(default=None, ge=0, le=10)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LessonMediaResponse(BaseModel):
    id: str
    media_type: MediaType
    title: str
    media_url: str
    mime_type: str
    file_size_bytes: int | None
    duration_seconds: int | None
    transcript: str | None
    caption_url: str | None
    sort_order: int
    is_published: bool
    created_at: datetime


class LessonMediaProgressUpdate(BaseModel):
    media_id: str = Field(min_length=1, max_length=64)
    position_seconds: int = Field(ge=0, le=86_400)
    completed: bool = False


class LessonMediaProgressResponse(BaseModel):
    position_seconds: int = Field(ge=0)
    completed: bool
    updated_at: datetime | None = None


class LessonMediaUrlCreateRequest(BaseModel):
    media_type: MediaType
    title: str = Field(min_length=1, max_length=160)
    source_url: str = Field(min_length=8, max_length=2048)
    mime_type: str = Field(min_length=3, max_length=120)
    duration_seconds: int | None = Field(default=None, ge=1, le=86_400)
    transcript: str | None = Field(default=None, max_length=100_000)
    caption_url: str | None = Field(default=None, max_length=2048)
    sort_order: int = Field(default=0, ge=0, le=999)
    is_published: bool = True

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("title must contain non-whitespace characters")
        return cleaned

    @field_validator("source_url", "caption_url")
    @classmethod
    def clean_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("transcript")
    @classmethod
    def clean_transcript(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LessonResponse(BaseModel):
    id: str
    course_code: str
    course_title: str
    unit_number: int
    unit_title: str
    lesson_number: int
    title: str
    skill: str
    content_type: str
    summary: str
    body: str
    transcript: str | None
    content_pack: dict = Field(default_factory=dict)
    source_attribution: str | None
    license_name: str | None
    media_url: str | None
    media: list[LessonMediaResponse] = Field(default_factory=list)
    duration_minutes: int
    progress_status: str | None
    progress_score: float | None
    completed_at: datetime | None
    media_progress: dict[str, LessonMediaProgressResponse] = Field(default_factory=dict)


class ClassCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "description")
    @classmethod
    def clean_class_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("value must contain non-whitespace characters")
        return cleaned


class ClassJoinRequest(BaseModel):
    invite_code: str = Field(min_length=6, max_length=24)

    @field_validator("invite_code")
    @classmethod
    def normalize_invite_code(cls, value: str) -> str:
        return value.strip().upper()


class ClassResponse(BaseModel):
    id: str
    teacher_id: str
    teacher_name: str
    name: str
    description: str | None
    invite_code: str | None
    member_count: int
    created_at: datetime
    updated_at: datetime | None
    learning_space_id: str | None = None


class ClassListResponse(BaseModel):
    items: list[ClassResponse]
    total: int


class ClassMemberResponse(BaseModel):
    id: str
    learner_id: str
    email: EmailStr
    display_name: str
    level: str | None
    joined_at: datetime


class ClassMemberListResponse(BaseModel):
    items: list[ClassMemberResponse]
    total: int


class AssignmentCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    skill: AnalysisType
    content: str = Field(min_length=3, max_length=10000)
    estimated_minutes: int = Field(ge=5, le=120)
    due_at: datetime

    @field_validator("title", "content")
    @classmethod
    def clean_assignment_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("value must contain non-whitespace characters")
        return cleaned

    @field_validator("due_at")
    @classmethod
    def require_future_deadline(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("due_at must include a timezone")
        if value.astimezone(UTC) <= datetime.now(UTC):
            raise ValueError("due_at must be in the future")
        return value


class AssignmentResponse(BaseModel):
    id: str
    class_id: str
    class_name: str
    created_by_id: str
    title: str
    skill: AnalysisType
    content: str
    estimated_minutes: int
    due_at: datetime
    created_at: datetime
    updated_at: datetime | None
    submission_id: str | None = None
    submission_status: str | None = None
    teacher_feedback: str | None = None


class AssignmentListResponse(BaseModel):
    items: list[AssignmentResponse]
    total: int


class AssignmentSubmitRequest(BaseModel):
    input_text: str = Field(min_length=3, max_length=10000)

    @field_validator("input_text")
    @classmethod
    def clean_submission(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("input_text must contain at least 3 non-whitespace characters")
        return cleaned


class SubmissionFeedbackUpdate(BaseModel):
    feedback: str = Field(min_length=1, max_length=4000)

    @field_validator("feedback")
    @classmethod
    def clean_feedback(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("feedback must contain non-whitespace characters")
        return cleaned


class AssignmentSubmissionResponse(BaseModel):
    id: str
    assignment_id: str
    learner_id: str
    learner_name: str
    status: str
    input_text: str
    analysis: AnalysisResponse | None
    teacher_feedback: str | None
    submitted_at: datetime
    feedback_at: datetime | None
    updated_at: datetime | None


class AssignmentSubmissionListResponse(BaseModel):
    items: list[AssignmentSubmissionResponse]
    total: int


class HomeClassAssignmentResponse(BaseModel):
    assignment_id: str
    class_id: str
    class_name: str
    title: str
    skill: AnalysisType
    content: str
    estimated_minutes: int
    due_at: datetime
    submission_id: str | None
    submission_status: str | None
    teacher_feedback: str | None


class HomePersonalTaskResponse(BaseModel):
    learning_path_id: str
    day: int
    title: str
    skill: str
    activity: str
    duration_minutes: int
    success_criteria: str


class HomeResponse(BaseModel):
    space_id: str
    space_kind: LearningSpaceKind
    space_name: str
    course_code: str | None
    goal: str | None
    current_level: str | None
    daily_minutes: int
    class_assignment_minutes: int
    remaining_personal_minutes: int
    total_planned_minutes: int
    class_assignments: list[HomeClassAssignmentResponse]
    personal_learning_path: LearningPathResponse | None
    next_personal_task: HomePersonalTaskResponse | None


class VocabularyCreateRequest(BaseModel):
    word: str = Field(min_length=1, max_length=120)
    meaning: str = Field(min_length=1, max_length=2000)
    example: str | None = Field(default=None, max_length=4000)
    analysis_id: str | None = Field(default=None, max_length=64)

    @field_validator("word", "meaning", "example")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("value must contain non-whitespace characters")
        return cleaned


class VocabularyUpdateRequest(BaseModel):
    status: Literal["new", "learning", "mastered"] | None = None
    example: str | None = Field(default=None, max_length=4000)

    @field_validator("example")
    @classmethod
    def clean_example(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class VocabularyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    word: str
    meaning: str
    example: str | None
    status: Literal["new", "learning", "mastered"]
    review_count: int
    analysis_id: str | None
    created_at: datetime
    updated_at: datetime | None


class VocabularyListResponse(BaseModel):
    items: list[VocabularyResponse]
    total: int


class WordPhoneticResponse(BaseModel):
    text: str | None = Field(default=None, max_length=120)
    audio_url: str | None = Field(default=None, max_length=2048, pattern=r"^https://")


class WordMeaningResponse(BaseModel):
    part_of_speech: str = Field(default="", max_length=80)
    definitions: list[str] = Field(default_factory=list, max_length=5)
    examples: list[str] = Field(default_factory=list, max_length=5)


class WordLookupResponse(BaseModel):
    word: str = Field(min_length=1, max_length=120)
    phonetics: list[WordPhoneticResponse] = Field(default_factory=list, max_length=8)
    meanings: list[WordMeaningResponse] = Field(default_factory=list, max_length=12)
    synonyms: list[str] = Field(default_factory=list, max_length=8)
    antonyms: list[str] = Field(default_factory=list, max_length=8)
    collocations: list[str] = Field(default_factory=list, max_length=8)
    cached: bool


class MessageResponse(BaseModel):
    message: str


class AdminStatsTrendItem(BaseModel):
    date: str
    count: int


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    new_users_last_7_days: int
    total_analyses: int
    analyses_today: int
    total_learning_paths: int
    learning_paths_today: int
    analyses_by_type: dict[str, int]
    analyses_last_7_days: list[AdminStatsTrendItem]


class AdminUserResponse(UserResponse):
    analysis_count: int
    updated_at: datetime | None
    last_login_at: datetime | None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    role: Literal["learner", "teacher", "admin"] | None = None

    @model_validator(mode="after")
    def require_change(self):
        if self.is_active is None and self.role is None:
            raise ValueError("At least one user field must be changed")
        return self


class AdminTeacherApplicationResponse(TeacherApplicationResponse):
    applicant_email: EmailStr
    applicant_display_name: str
    reviewer_email: EmailStr | None


class AdminTeacherApplicationListResponse(BaseModel):
    items: list[AdminTeacherApplicationResponse]
    total: int


class AdminAnalysisResponse(AnalysisResponse):
    user_id: str
    user_email: EmailStr
    user_display_name: str


class AdminAnalysisListResponse(BaseModel):
    items: list[AdminAnalysisResponse]
    total: int


class AdminAnalysisJobResponse(BaseModel):
    id: str
    user_id: str
    user_email: EmailStr
    user_display_name: str
    type: AnalysisType
    status: AnalysisJobStatus
    analysis_id: str | None
    provider: str | None
    error_message: str | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime | None


class AdminAnalysisJobListResponse(BaseModel):
    items: list[AdminAnalysisJobResponse]
    total: int


class AdminLearningPathResponse(LearningPathResponse):
    user_id: str
    user_email: EmailStr
    user_display_name: str


class AdminLearningPathListResponse(BaseModel):
    items: list[AdminLearningPathResponse]
    total: int


class AdminAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    admin_user_id: str | None
    admin_email: EmailStr | None
    action: str
    target_type: str
    target_id: str | None
    details: dict
    created_at: datetime


class AdminAuditLogListResponse(BaseModel):
    items: list[AdminAuditLogResponse]
    total: int
