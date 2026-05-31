"""Shared pytest fixtures for server tests."""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import create_app
from app.database import get_db
from app.models.models import Base
from app.services.auth_service import hash_password, create_token
from datetime import timedelta


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    """HTTPX async client with in-memory SQLite override."""
    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def teacher_token(client):
    """Create a teacher and return their JWT."""
    from app.models.models import User
    from sqlalchemy import insert

    # Use db through the app's override
    # Simpler: create token directly
    token = create_token(
        {"sub": "999", "role": "teacher"},
        timedelta(hours=1),
    )
    return token


@pytest_asyncio.fixture
async def seeded_db(db_engine):
    """Seed a teacher, exam, student, and commits."""
    from app.models.models import User, Exam, ExamSession, Commit
    from app.services.auth_service import hash_password
    from sqlalchemy.ext.asyncio import AsyncSession

    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        teacher = User(email="t@test.com", role="teacher", password_hash=hash_password("pass"))
        session.add(teacher)
        await session.flush()

        exam = Exam(
            teacher_id=teacher.user_id,
            name="Test Exam",
            group_number="G1",
            exam_date="2026-06-01",
            duration_minutes=90,
        )
        session.add(exam)
        await session.flush()

        student = User(email="s@test.com", role="student")
        session.add(student)
        await session.flush()

        sess = ExamSession(exam_id=exam.exam_id, student_id=student.user_id, variant=1)
        session.add(sess)
        await session.flush()

        commit = Commit(
            commit_id="abc123",
            student_id=student.user_id,
            exam_id=exam.exam_id,
            timestamp="2026-06-01T08:05:00Z",
            exercise_id="ex1",
            file_name="solution.py",
            lines_added=10,
            lines_removed=2,
        )
        session.add(commit)
        await session.commit()

        return {
            "teacher": teacher,
            "exam": exam,
            "student": student,
            "session": sess,
            "commit": commit,
            "teacher_token": create_token(
                {"sub": str(teacher.user_id), "role": "teacher"},
                timedelta(hours=1),
            ),
            "student_token": create_token(
                {
                    "sub": str(student.user_id),
                    "role": "student",
                    "exam_id": exam.exam_id,
                    "session_id": sess.session_id,
                },
                timedelta(hours=2),
            ),
        }
