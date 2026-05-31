"""Seed script to insert a test teacher into the database.

Run with:
    python -m app.seed
"""

import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal, engine
from app.models.models import Base, User
from app.services.auth_service import hash_password

TEACHER_EMAIL = "teacher@test.com"
TEACHER_PASSWORD = "secret"


async def seed() -> None:
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == TEACHER_EMAIL, User.role == "teacher")
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"Teacher already exists: {TEACHER_EMAIL} (user_id={existing.user_id})")
            return

        teacher = User(
            email=TEACHER_EMAIL,
            role="teacher",
            password_hash=hash_password(TEACHER_PASSWORD),
            group_number=None,
        )
        db.add(teacher)
        await db.commit()
        await db.refresh(teacher)
        print(f"Created teacher: {TEACHER_EMAIL} (user_id={teacher.user_id})")


if __name__ == "__main__":
    asyncio.run(seed())
