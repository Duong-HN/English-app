from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import require_learner
from ..models import PlacementAttempt, User, utc_now
from ..placement import PLACEMENT_QUESTIONS, PLACEMENT_TEST_VERSION, public_questions, score_answers
from ..schemas import (
    PlacementResultResponse,
    PlacementSubmitRequest,
    PlacementTestResponse,
)

router = APIRouter(prefix="/placement-test", tags=["placement test"])


@router.get("", response_model=PlacementTestResponse)
def get_placement_test():
    return PlacementTestResponse(
        questions=public_questions(),
        total_questions=len(PLACEMENT_QUESTIONS),
        test_version=PLACEMENT_TEST_VERSION,
    )


@router.post("/submit", response_model=PlacementResultResponse, status_code=status.HTTP_201_CREATED)
def submit_placement_test(
    request: PlacementSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    valid_ids = {question.id for question in PLACEMENT_QUESTIONS}
    submitted_ids = set(request.answers)
    invalid_options = {answer for answer in request.answers.values() if answer not in {"a", "b", "c", "d"}}
    if submitted_ids != valid_ids or invalid_options:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Submit exactly one answer (a, b, c or d) for every placement question",
        )
    score, level, skill_scores = score_answers(request.answers)
    attempt = PlacementAttempt(
        user_id=user.id,
        score=score,
        total_questions=len(PLACEMENT_QUESTIONS),
        level=level,
        answers=request.answers,
        skill_scores=skill_scores,
        test_version=PLACEMENT_TEST_VERSION,
        completed_at=utc_now(),
    )
    user.level = level
    user.updated_at = utc_now()
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return PlacementResultResponse.model_validate(attempt)


@router.get("/latest", response_model=PlacementResultResponse)
def latest_placement_result(
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    attempt = db.scalar(
        select(PlacementAttempt)
        .where(PlacementAttempt.user_id == user.id)
        .order_by(PlacementAttempt.completed_at.desc())
        .limit(1)
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placement test not completed")
    return PlacementResultResponse.model_validate(attempt)
