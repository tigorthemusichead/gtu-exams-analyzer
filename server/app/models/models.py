"""SQLAlchemy ORM models matching the cheat-buster DB schema."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Float,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
    )

    __table_args__ = (
        CheckConstraint("role IN ('student', 'teacher')", name="ck_users_role"),
    )

    # Relationships
    exams_taught: Mapped[list["Exam"]] = relationship(
        "Exam", back_populates="teacher", foreign_keys="[Exam.teacher_id]"
    )
    exam_sessions: Mapped[list["ExamSession"]] = relationship(
        "ExamSession", back_populates="student", foreign_keys="[ExamSession.student_id]"
    )
    commits: Mapped[list["Commit"]] = relationship(
        "Commit", back_populates="student", foreign_keys="[Commit.student_id]"
    )
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="student",
        foreign_keys="[AnalysisResult.student_id]",
    )


class Exam(Base):
    __tablename__ = "exams"

    exam_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    group_number: Mapped[str] = mapped_column(Text, nullable=False)
    exam_date: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="90"
    )
    created_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
    )

    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_exams_duration_positive"),
    )

    # Relationships
    teacher: Mapped["User"] = relationship(
        "User", back_populates="exams_taught", foreign_keys=[teacher_id]
    )
    sessions: Mapped[list["ExamSession"]] = relationship(
        "ExamSession", back_populates="exam"
    )
    commits: Mapped[list["Commit"]] = relationship("Commit", back_populates="exam")
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult", back_populates="exam"
    )
    similarity_pairs: Mapped[list["SimilarityPair"]] = relationship(
        "SimilarityPair", back_populates="exam"
    )


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.exam_id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    variant: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
    )
    ended_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_sessions_exam_student"),
    )

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="sessions")
    student: Mapped["User"] = relationship(
        "User", back_populates="exam_sessions", foreign_keys=[student_id]
    )


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commit_id: Mapped[str] = mapped_column(Text, nullable=False)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.exam_id"), nullable=False
    )
    timestamp: Mapped[str] = mapped_column(Text, nullable=False)
    exercise_id: Mapped[str] = mapped_column(Text, nullable=False)
    lines_added: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    lines_removed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    diff_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "commit_id", "student_id", "file_name", name="uq_commits_commit_student_file"
        ),
        CheckConstraint("lines_added >= 0", name="ck_commits_lines_added"),
        CheckConstraint("lines_removed >= 0", name="ck_commits_lines_removed"),
    )

    # Relationships
    student: Mapped["User"] = relationship(
        "User", back_populates="commits", foreign_keys=[student_id]
    )
    exam: Mapped["Exam"] = relationship("Exam", back_populates="commits")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.exam_id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    normality_score: Mapped[float] = mapped_column(Float, nullable=False)
    suspicious_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
    )

    __table_args__ = (
        UniqueConstraint(
            "exam_id", "student_id", name="uq_analysis_results_exam_student"
        ),
    )

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="analysis_results")
    student: Mapped["User"] = relationship(
        "User", back_populates="analysis_results", foreign_keys=[student_id]
    )


class SimilarityPair(Base):
    __tablename__ = "similarity_pairs"

    pair_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.exam_id"), nullable=False
    )
    student_a_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    student_b_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
    )

    __table_args__ = (
        CheckConstraint("student_a_id < student_b_id", name="ck_similarity_pairs_order"),
        CheckConstraint(
            "similarity_score >= 0", name="ck_similarity_pairs_score_positive"
        ),
        UniqueConstraint(
            "exam_id",
            "student_a_id",
            "student_b_id",
            name="uq_similarity_pairs_exam_a_b",
        ),
    )

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="similarity_pairs")
    student_a: Mapped["User"] = relationship(
        "User", foreign_keys=[student_a_id]
    )
    student_b: Mapped["User"] = relationship(
        "User", foreign_keys=[student_b_id]
    )
