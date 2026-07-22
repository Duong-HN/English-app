from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .ai_schemas import LearningPathResult

AnalysisType = Literal["reading", "writing", "speaking"]
LearningLevel = Literal["A1", "A2", "B1", "B2", "C1"]
UserRole = Literal["learner", "teacher", "admin"]
MembershipStatus = Literal["pending", "active", "removed"]
MembershipUpdateStatus = Literal["active", "removed"]
AssignmentStatus = Literal["published", "closed"]


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


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    role: UserRole
    level: str | None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AnalysisRequest(BaseModel):
    input_text: str = Field(min_length=3, max_length=10000)

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
    created_at: datetime


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


class LearningPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    goal: str
    current_level: LearningLevel
    minutes_per_day: int
    plan: LearningPathResult
    provider: str
    created_at: datetime


class LearningPathListResponse(BaseModel):
    items: list[LearningPathResponse]
    total: int


class MessageResponse(BaseModel):
    message: str


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=4000)
    target_level: LearningLevel | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("name must contain at least 2 non-whitespace characters")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return value.strip()


class ClassroomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    target_level: LearningLevel | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("name must contain at least 2 non-whitespace characters")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_optional_description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one class field must be changed")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        if "description" in self.model_fields_set and self.description is None:
            raise ValueError("description cannot be null")
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("is_active cannot be null")
        return self


class ClassroomJoinRequest(BaseModel):
    join_code: str = Field(min_length=6, max_length=16)

    @field_validator("join_code")
    @classmethod
    def normalize_join_code(cls, value: str) -> str:
        return value.strip().upper()


class ClassroomJoinCodeResponse(BaseModel):
    join_code: str
    updated_at: datetime


class ManagedClassroomResponse(BaseModel):
    id: str
    teacher_id: str
    teacher_email: EmailStr
    teacher_display_name: str
    name: str
    description: str
    target_level: LearningLevel | None
    join_code: str
    is_active: bool
    active_member_count: int
    pending_member_count: int
    assignment_count: int
    created_at: datetime
    updated_at: datetime | None


class ManagedClassroomListResponse(BaseModel):
    items: list[ManagedClassroomResponse]
    total: int


class LearnerClassroomResponse(BaseModel):
    id: str
    teacher_id: str
    teacher_email: EmailStr
    teacher_display_name: str
    name: str
    description: str
    target_level: LearningLevel | None
    is_active: bool
    membership_id: str
    membership_status: MembershipStatus
    joined_at: datetime
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class LearnerClassroomListResponse(BaseModel):
    items: list[LearnerClassroomResponse]
    total: int


class ClassroomMemberUpdate(BaseModel):
    status: MembershipUpdateStatus


class ClassroomMemberResponse(BaseModel):
    id: str
    class_id: str
    learner_id: str
    learner_email: EmailStr
    learner_display_name: str
    learner_level: str | None
    learner_is_active: bool
    status: MembershipStatus
    joined_at: datetime
    approved_at: datetime | None
    updated_at: datetime | None


class ClassroomMemberListResponse(BaseModel):
    items: list[ClassroomMemberResponse]
    total: int


class ClassAssignmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    instructions: str = Field(min_length=3, max_length=10000)
    skill_type: AnalysisType
    target_level: LearningLevel | None = None
    due_at: datetime | None = None
    status: AssignmentStatus = "published"

    @field_validator("title", "instructions")
    @classmethod
    def clean_assignment_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("assignment text cannot be blank")
        return cleaned

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("due_at must include a timezone")
        return value.astimezone(UTC)


class ClassAssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    instructions: str | None = Field(default=None, min_length=3, max_length=10000)
    target_level: LearningLevel | None = None
    due_at: datetime | None = None
    status: AssignmentStatus | None = None

    @field_validator("title", "instructions")
    @classmethod
    def clean_optional_assignment_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("assignment text cannot be blank")
        return cleaned

    @field_validator("due_at")
    @classmethod
    def require_optional_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("due_at must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one assignment field must be changed")
        for field in ("title", "instructions", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ClassAssignmentResponse(BaseModel):
    id: str
    class_id: str
    class_name: str
    created_by_id: str
    created_by_display_name: str
    title: str
    instructions: str
    skill_type: AnalysisType
    target_level: LearningLevel | None
    due_at: datetime | None
    status: AssignmentStatus
    submission_count: int
    my_submission_count: int
    created_at: datetime
    updated_at: datetime | None


class ClassAssignmentListResponse(BaseModel):
    items: list[ClassAssignmentResponse]
    total: int


class AssignmentSubmissionCreate(BaseModel):
    analysis_id: str = Field(min_length=1, max_length=64)


class AssignmentSubmissionResponse(BaseModel):
    id: str
    assignment_id: str
    learner_id: str
    learner_email: EmailStr
    learner_display_name: str
    analysis_id: str
    attempt_number: int
    status: Literal["submitted"]
    submitted_at: datetime
    analysis: AnalysisResponse


class AssignmentSubmissionListResponse(BaseModel):
    items: list[AssignmentSubmissionResponse]
    total: int


class AdminStatsTrendItem(BaseModel):
    date: str
    count: int


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    teacher_users: int
    new_users_last_7_days: int
    total_analyses: int
    analyses_today: int
    total_learning_paths: int
    learning_paths_today: int
    total_classes: int
    active_classes: int
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
    role: UserRole | None = None

    @model_validator(mode="after")
    def require_change(self):
        if self.is_active is None and self.role is None:
            raise ValueError("At least one user field must be changed")
        return self


class AdminAnalysisResponse(AnalysisResponse):
    user_id: str
    user_email: EmailStr
    user_display_name: str


class AdminAnalysisListResponse(BaseModel):
    items: list[AdminAnalysisResponse]
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
