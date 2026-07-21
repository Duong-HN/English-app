from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AnalysisType = Literal["reading", "writing", "speaking"]


class AnalysisRequest(BaseModel):
    input_text: str = Field(min_length=3, max_length=10000)


class AnalysisResponse(BaseModel):
    id: str
    type: AnalysisType
    input_text: str
    result: dict
    score: float | None
    provider: str
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[AnalysisResponse]
