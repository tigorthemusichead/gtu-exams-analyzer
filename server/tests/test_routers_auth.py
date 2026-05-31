"""Integration tests for /auth/student and /auth/teacher endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.main import create_app
from app.database import get_db
from app.models.models import Base, User, Exam
from app.services.auth_service import hash_password


@pytest.mark.asyncio
async def test_teacher_login_success(client, db_engine):
    # Seed teacher
    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        teacher = User(email="teacher@x.com", role="teacher", password_hash=hash_password("pass123"))
        session.add(teacher)
        await session.commit()

    res = await client.post("/auth/teacher", json={"email": "teacher@x.com", "password": "pass123"})
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert res.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_teacher_login_wrong_password(client, db_engine):
    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        teacher = User(email="t2@x.com", role="teacher", password_hash=hash_password("correct"))
        session.add(teacher)
        await session.commit()

    res = await client.post("/auth/teacher", json={"email": "t2@x.com", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_teacher_login_not_found(client):
    res = await client.post("/auth/teacher", json={"email": "ghost@x.com", "password": "x"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_student_auth_creates_user_and_returns_token(client, db_engine):
    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        teacher = User(email="t3@x.com", role="teacher", password_hash=hash_password("p"))
        session.add(teacher)
        await session.flush()
        exam = Exam(
            teacher_id=teacher.user_id,
            name="E1",
            group_number="G1",
            exam_date="2026-06-01",
            duration_minutes=60,
        )
        session.add(exam)
        await session.commit()
        exam_id = exam.exam_id

    res = await client.post("/auth/student", json={
        "email": "student@x.com",
        "group_number": "G1",
        "exam_id": exam_id,
        "variant": 1,
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_student_auth_unknown_exam(client):
    res = await client.post("/auth/student", json={
        "email": "s@x.com",
        "group_number": "G1",
        "exam_id": 99999,
        "variant": 1,
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_missing_token_returns_4xx(client):
    res = await client.get("/exams")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_wrong_role_returns_403(client, seeded_db):
    """Student token rejected on teacher-only endpoint."""
    token = seeded_db["student_token"]
    res = await client.get("/exams", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
