from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_student
from app.models.models import Commit
from app.schemas.schemas import CommitIngestionRequest, CommitIngestionResponse

router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CommitIngestionResponse,
)
async def ingest_commits(
    body: CommitIngestionRequest,
    payload: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db),
) -> CommitIngestionResponse:
    """Batch-insert commits for the authenticated student.

    - student_id and exam_id come from the JWT payload (never from the body).
    - Duplicate rows (same commit_id + student_id + file_name) are silently ignored.
    - Returns the count of rows actually inserted.
    """
    student_id: int = int(payload["sub"])
    exam_id: int = int(payload["exam_id"])

    inserted_count = 0

    for item in body.commits:
        stmt = (
            insert(Commit)
            .prefix_with("OR IGNORE")
            .values(
                commit_id=item.commit_id,
                student_id=student_id,
                exam_id=exam_id,
                timestamp=item.timestamp,
                exercise_id=item.exercise_id,
                file_name=item.file_name,
                lines_added=item.lines_added,
                lines_removed=item.lines_removed,
                diff_content=item.diff,
            )
        )
        try:
            result = await db.execute(stmt)
            # rowcount == 1 means the row was inserted; 0 means it was ignored
            if result.rowcount == 1:
                inserted_count += 1
        except IntegrityError:
            # Fallback: if OR IGNORE somehow didn't suppress the error, skip row
            await db.rollback()

    await db.commit()

    return CommitIngestionResponse(inserted=inserted_count)
