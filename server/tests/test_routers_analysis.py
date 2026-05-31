"""Integration tests for /analysis and /reports endpoints."""

import pytest


@pytest.mark.asyncio
async def test_trigger_analysis_success(client, seeded_db):
    token = seeded_db["teacher_token"]
    exam_id = seeded_db["exam"].exam_id
    res = await client.post(f"/analysis/{exam_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["exam_id"] == exam_id
    assert data["status"] == "completed"
    assert data["individual_count"] >= 1


@pytest.mark.asyncio
async def test_trigger_analysis_exam_not_found(client, seeded_db):
    token = seeded_db["teacher_token"]
    res = await client.post("/analysis/99999", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_trigger_analysis_wrong_teacher(client, seeded_db, db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from app.models.models import User
    from app.services.auth_service import hash_password, create_token
    from datetime import timedelta

    Session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        other = User(email="other2@x.com", role="teacher", password_hash=hash_password("x"))
        session.add(other)
        await session.commit()
        other_token = create_token({"sub": str(other.user_id), "role": "teacher"}, timedelta(hours=1))

    exam_id = seeded_db["exam"].exam_id
    res = await client.post(f"/analysis/{exam_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_get_report_after_analysis(client, seeded_db):
    token = seeded_db["teacher_token"]
    exam_id = seeded_db["exam"].exam_id

    # Run analysis first
    await client.post(f"/analysis/{exam_id}", headers={"Authorization": f"Bearer {token}"})

    res = await client.get(f"/reports/{exam_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["exam_id"] == exam_id
    assert "individual" in data
    assert "group" in data
    assert isinstance(data["suspects"], list)


@pytest.mark.asyncio
async def test_get_report_404_no_exam(client, seeded_db):
    token = seeded_db["teacher_token"]
    res = await client.get("/reports/99999", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_analysis_requires_teacher(client, seeded_db):
    token = seeded_db["student_token"]
    exam_id = seeded_db["exam"].exam_id
    res = await client.post(f"/analysis/{exam_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
