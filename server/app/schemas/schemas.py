"""Pydantic request/response schemas for cheat-buster."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    role: Literal["student", "teacher"]
    password: str | None = None
    group_number: str | None = None


class UserOut(BaseModel):
    user_id: int
    email: str
    role: str
    group_number: str | None
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Exams
# ---------------------------------------------------------------------------


class ExamCreate(BaseModel):
    name: str
    group_number: str
    exam_date: str
    duration_minutes: int = 90


class ExamOut(BaseModel):
    exam_id: int
    teacher_id: int
    name: str
    group_number: str
    exam_date: str
    duration_minutes: int
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Exam Sessions
# ---------------------------------------------------------------------------


class ExamSessionCreate(BaseModel):
    exam_id: int
    student_id: int
    variant: int


class ExamSessionOut(BaseModel):
    session_id: int
    exam_id: int
    student_id: int
    variant: int
    started_at: str
    ended_at: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Commits
# ---------------------------------------------------------------------------


class CommitIn(BaseModel):
    commit_id: str
    timestamp: str
    exercise_id: str
    lines_added: int = 0
    lines_removed: int = 0
    file_name: str


class CommitOut(BaseModel):
    id: int
    commit_id: str
    student_id: int
    exam_id: int
    timestamp: str
    exercise_id: str
    lines_added: int
    lines_removed: int
    file_name: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Analysis Results
# ---------------------------------------------------------------------------


class AnalysisResultOut(BaseModel):
    result_id: int
    exam_id: int
    student_id: int
    normality_score: float
    suspicious_flags: str | None
    analyzed_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Similarity Pairs
# ---------------------------------------------------------------------------


class SimilarityPairOut(BaseModel):
    pair_id: int
    exam_id: int
    student_a_id: int
    student_b_id: int
    similarity_score: float
    details: str | None
    analyzed_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class StudentAuthRequest(BaseModel):
    email: str
    group_number: str
    exam_id: int
    variant: int


class TeacherAuthRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Exam management (TASK-005)
# ---------------------------------------------------------------------------


from pydantic import ConfigDict


class ExamCreate(BaseModel):
    name: str
    group_number: str
    date: str          # ISO 8601 e.g. "2026-06-01"
    duration_minutes: int


class ExamResponse(BaseModel):
    exam_id: int
    name: str
    group_number: str
    exam_date: str
    duration_minutes: int
    created_at: str
    has_report: bool = False
    participant_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Commit ingestion (TASK-006)
# ---------------------------------------------------------------------------


class CommitIngestionItem(BaseModel):
    commit_id: str
    timestamp: str          # ISO 8601
    exercise_id: str
    file_name: str
    lines_added: int = 0
    lines_removed: int = 0
    diff: str | None = None   # optional, ignored for now (MVP)


class CommitIngestionRequest(BaseModel):
    commits: list[CommitIngestionItem]


class CommitIngestionResponse(BaseModel):
    inserted: int


# ---------------------------------------------------------------------------
# Analysis / Report (TASK-009)
# ---------------------------------------------------------------------------


class AnomalyEventSchema(BaseModel):
    type: str
    timestamp: str
    detail: str


class IndividualResultSchema(BaseModel):
    student_id: int
    anomaly_score: float
    events: list[AnomalyEventSchema]


class SimilarityEdgeSchema(BaseModel):
    student_a: int
    student_b: int
    score: float
    details: dict


class GroupResultSchema(BaseModel):
    nodes: list[int]
    edges: list[SimilarityEdgeSchema]


class ReportResponse(BaseModel):
    exam_id: int
    generated_at: str
    individual: list[IndividualResultSchema]
    group: GroupResultSchema
    suspects: list[int]  # student_ids above threshold


class AnalysisTriggerResponse(BaseModel):
    exam_id: int
    status: str  # "completed"
    individual_count: int
    edge_count: int
