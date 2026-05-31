"""Integration tests for /exams endpoints."""

import pytest
from datetime import timedelta

from app.services.auth_service import create_token


def teacher_token(teacher_id: int) -> str:
    return create_token({"sub": str(teacher_id), "role": "teacher"}, timedelta(hours=1))


def student_token(student_id: int, exam_id: int) -> str:
    return create_token(
        {"sub": str(student_id), "role": "student", "exam_id": exam_id, "session_id": 1},
        timedelta(hours=1),
    )


@pytest.mark.asyncio
async def test_create_exam(client, seeded_db):
    token = seeded_db["teacher_token"]
    res = await client.post(
        "/exams",
        json={"name": "New Exam", "group_number": "G2", "date": "2026-07-01", "duration_minutes": 120},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "New Exam"
    assert data["duration_minutes"] == 120
    assert data["has_report"] is False
    assert data["participant_count"] == 0


@pytest.mark.asyncio
async def test_list_exams(client, seeded_db):
    token = seeded_db["teacher_token"]
    res = await client.get("/exams", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    exams = res.json()
    assert isinstance(exams, list)
    assert len(exams) >= 1


@pytest.mark.asyncio
async def test_get_exam(client, seeded_db):
    token = seeded_db["teacher_token"]
    exam_id = seeded_db["exam"].exam_id
    res = await client.get(f"/exams/{exam_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["exam_id"] == exam_id


@pytest.mark.asyncio
async def test_get_exam_not_found(client, seeded_db):
    token = seeded_db["teacher_token"]
    res = await client.get("/exams/99999", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_exam_requires_teacher(client, seeded_db):
    token = seeded_db["student_token"]
    res = await client.post(
        "/exams",
        json={"name": "X", "group_number": "G", "date": "2026-01-01", "duration_minutes": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_get_exam_wrong_teacher(client, seeded_db, db_engine):
    """Teacher that doesn't own the exam gets 403."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from app.models.models import User
    from app.services.auth_service import hash_password

    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        other = User(email="other@x.com", role="teacher", password_hash=hash_password("x"))
        session.add(other)
        await session.commit()
        other_token = create_token({"sub": str(other.user_id), "role": "teacher"}, timedelta(hours=1))

    exam_id = seeded_db["exam"].exam_id
    res = await client.get(f"/exams/{exam_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res.status_code == 403
