"""Authentication endpoints for students and teachers."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import Exam, ExamSession, User
from app.schemas.schemas import StudentAuthRequest, TeacherAuthRequest, TokenResponse
from app.services.auth_service import create_token, hash_password, verify_password

router = APIRouter()


@router.post("/student", response_model=TokenResponse)
async def student_auth(body: StudentAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a student and return a scoped JWT."""
    # 1. Look up exam
    result = await db.execute(select(Exam).where(Exam.exam_id == body.exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    # 2. Look up or create student user
    result = await db.execute(
        select(User).where(User.email == body.email, User.role == "student")
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=body.email,
            role="student",
            password_hash=None,
            group_number=body.group_number,
        )
        db.add(user)
        await db.flush()  # populate user.user_id without full commit

    # 3. Look up or create exam session
    result = await db.execute(
        select(ExamSession).where(
            ExamSession.exam_id == body.exam_id,
            ExamSession.student_id == user.user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        session = ExamSession(
            exam_id=body.exam_id,
            student_id=user.user_id,
            variant=body.variant,
        )
        db.add(session)
        await db.flush()

    await db.commit()

    # 4. Create JWT scoped to this exam session
    token = create_token(
        payload={
            "sub": str(user.user_id),
            "role": "student",
            "exam_id": body.exam_id,
            "session_id": session.session_id,
        },
        expires_delta=timedelta(minutes=exam.duration_minutes),
    )

    return TokenResponse(access_token=token)


@router.post("/teacher", response_model=TokenResponse)
async def teacher_auth(
    body: TeacherAuthRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a teacher and return a long-lived JWT."""
    # 1. Look up teacher
    result = await db.execute(
        select(User).where(User.email == body.email, User.role == "teacher")
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Verify password
    if not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Create JWT valid for 8 hours
    token = create_token(
        payload={"sub": str(user.user_id), "role": "teacher"},
        expires_delta=timedelta(hours=8),
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="strict",
        max_age=8 * 3600,
    )
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(response: Response):
    """Clear the teacher session cookie."""
    response.delete_cookie(key="access_token", samesite="strict")
    return {"ok": True}
