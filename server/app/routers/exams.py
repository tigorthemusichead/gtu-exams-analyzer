from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_teacher
from app.models.models import AnalysisResult, Exam, ExamSession
from app.schemas.schemas import ExamCreate, ExamResponse

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def _build_exam_response(exam: Exam, db: AsyncSession) -> ExamResponse:
    """Populate has_report and participant_count for an Exam ORM object."""
    # participant_count: count of distinct ExamSession rows for this exam
    participant_result = await db.execute(
        select(func.count(ExamSession.session_id)).where(
            ExamSession.exam_id == exam.exam_id
        )
    )
    participant_count: int = participant_result.scalar_one()

    # has_report: True if at least one AnalysisResult exists for this exam
    report_result = await db.execute(
        select(func.count(AnalysisResult.result_id)).where(
            AnalysisResult.exam_id == exam.exam_id
        )
    )
    has_report: bool = (report_result.scalar_one() or 0) > 0

    return ExamResponse(
        exam_id=exam.exam_id,
        name=exam.name,
        group_number=exam.group_number,
        exam_date=exam.exam_date,
        duration_minutes=exam.duration_minutes,
        created_at=exam.created_at,
        has_report=has_report,
        participant_count=participant_count,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ExamResponse)
async def create_exam(
    body: ExamCreate,
    payload: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
) -> ExamResponse:
    """Create a new exam (teacher only)."""
    teacher_id = int(payload["sub"])

    exam = Exam(
        teacher_id=teacher_id,
        name=body.name,
        group_number=body.group_number,
        exam_date=body.date,
        duration_minutes=body.duration_minutes,
        created_at=_now_iso(),
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    return await _build_exam_response(exam, db)


@router.get("", response_model=list[ExamResponse])
async def list_exams(
    payload: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
) -> list[ExamResponse]:
    """List all exams owned by the current teacher."""
    teacher_id = int(payload["sub"])

    result = await db.execute(
        select(Exam).where(Exam.teacher_id == teacher_id)
    )
    exams = result.scalars().all()

    return [await _build_exam_response(exam, db) for exam in exams]


@router.get("/{exam_id:int}", response_model=ExamResponse)
async def get_exam(
    exam_id: int,
    payload: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
) -> ExamResponse:
    """Return a single exam by ID (teacher only)."""
    teacher_id = int(payload["sub"])

    result = await db.execute(select(Exam).where(Exam.exam_id == exam_id))
    exam: Exam | None = result.scalar_one_or_none()

    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam {exam_id} not found",
        )

    if exam.teacher_id != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this exam",
        )

    return await _build_exam_response(exam, db)
