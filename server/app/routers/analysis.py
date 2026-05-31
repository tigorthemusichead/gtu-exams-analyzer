"""Analysis and report endpoints for cheat-buster (TASK-009)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import require_teacher
from app.models.models import (
    AnalysisResult,
    Commit,
    Exam,
    SimilarityPair,
)
from app.schemas.schemas import (
    AnalysisTriggerResponse,
    AnomalyEventSchema,
    GroupResultSchema,
    IndividualResultSchema,
    ReportResponse,
    SimilarityEdgeSchema,
)
from app.services.analysis_group import analyze_group
from app.services.analysis_individual import CommitRecord, analyze_student

router = APIRouter()

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _get_exam_or_raise(
    exam_id: int,
    teacher_id: int,
    db: AsyncSession,
) -> Exam:
    result = await db.execute(select(Exam).where(Exam.exam_id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if exam.teacher_id != teacher_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your exam")
    return exam


# ---------------------------------------------------------------------------
# POST /analysis/{exam_id}  — trigger analysis and persist results
# ---------------------------------------------------------------------------


@router.post("/analysis/{exam_id}", response_model=AnalysisTriggerResponse)
async def trigger_analysis(
    exam_id: int,
    payload: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
) -> AnalysisTriggerResponse:
    teacher_id: int = int(payload["sub"])
    exam = await _get_exam_or_raise(exam_id, teacher_id, db)

    # --- Load commits grouped by student ---
    commits_result = await db.execute(
        select(Commit).where(Commit.exam_id == exam_id)
    )
    all_commits = commits_result.scalars().all()

    commits_by_student: dict[int, list[CommitRecord]] = {}
    for c in all_commits:
        rec = CommitRecord(
            commit_id=c.commit_id,
            student_id=c.student_id,
            timestamp=c.timestamp,
            lines_added=c.lines_added,
            lines_removed=c.lines_removed,
            file_name=c.file_name,
            exercise_id=c.exercise_id,
            diff_content=c.diff_content,
        )
        commits_by_student.setdefault(c.student_id, []).append(rec)

    # --- Collect cohort first commits for late-start detection ---
    cohort_first_commits: list[str] = []
    for student_commits_iter in commits_by_student.values():
        sorted_sc = sorted(student_commits_iter, key=lambda c: c.timestamp)
        if sorted_sc:
            cohort_first_commits.append(sorted_sc[0].timestamp)

    # --- Individual analysis ---
    analyzed_at = _now_iso()
    individual_count = 0

    for student_id, student_commits in commits_by_student.items():
        result = analyze_student(
            student_id=student_id,
            commits=student_commits,
            cohort_first_commits=cohort_first_commits,
            burst_lines_threshold=settings.BURST_LINES_THRESHOLD,
            burst_window_seconds=settings.BURST_WINDOW_SECONDS,
            late_start_threshold_minutes=settings.LATE_START_THRESHOLD_MINUTES,
            inactivity_gap_minutes=settings.INACTIVITY_GAP_MINUTES,
        )

        normality_score = 1.0 - result.anomaly_score
        suspicious_flags = json.dumps(
            [{"type": e.type, "timestamp": e.timestamp, "detail": e.detail} for e in result.events]
        ) if result.events else None

        stmt = sqlite_insert(AnalysisResult).values(
            exam_id=exam_id,
            student_id=student_id,
            normality_score=normality_score,
            suspicious_flags=suspicious_flags,
            analyzed_at=analyzed_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["exam_id", "student_id"],
            set_={
                "normality_score": normality_score,
                "suspicious_flags": suspicious_flags,
                "analyzed_at": analyzed_at,
            },
        )
        await db.execute(stmt)
        individual_count += 1

    # --- Group analysis ---
    # Store ALL pairs (threshold=0) so the D3 report graph can filter client-side.
    # The SUSPECT_SIMILARITY_THRESHOLD is applied during report generation.
    group_result = analyze_group(
        commits_by_student=commits_by_student,
        weight_cosine=settings.SIMILARITY_WEIGHT_COSINE,
        weight_structural=settings.SIMILARITY_WEIGHT_STRUCTURAL,
        weight_sequential=settings.SIMILARITY_WEIGHT_SEQUENTIAL,
        edge_threshold=0.0,
        sequential_window_seconds=settings.SEQUENTIAL_WINDOW_SECONDS,
        sequential_content_threshold=settings.SEQUENTIAL_CONTENT_THRESHOLD,
        sequential_min_tokens=settings.SEQUENTIAL_MIN_TOKEN_COUNT,
    )

    edge_count = 0
    for edge in group_result.edges:
        a_id = min(edge.student_a, edge.student_b)
        b_id = max(edge.student_a, edge.student_b)
        details_json = json.dumps(edge.details)

        stmt = sqlite_insert(SimilarityPair).values(
            exam_id=exam_id,
            student_a_id=a_id,
            student_b_id=b_id,
            similarity_score=edge.score,
            details=details_json,
            analyzed_at=analyzed_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["exam_id", "student_a_id", "student_b_id"],
            set_={
                "similarity_score": edge.score,
                "details": details_json,
                "analyzed_at": analyzed_at,
            },
        )
        await db.execute(stmt)
        edge_count += 1

    await db.commit()

    return AnalysisTriggerResponse(
        exam_id=exam_id,
        status="completed",
        individual_count=individual_count,
        edge_count=edge_count,
    )


# ---------------------------------------------------------------------------
# GET /reports/{exam_id}  — return stored analysis results
# ---------------------------------------------------------------------------


@router.get("/reports/{exam_id}", response_model=ReportResponse)
async def get_report(
    exam_id: int,
    payload: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    teacher_id: int = int(payload["sub"])
    await _get_exam_or_raise(exam_id, teacher_id, db)

    # Load individual results
    ar_result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.exam_id == exam_id)
    )
    analysis_rows = ar_result.scalars().all()

    individual: list[IndividualResultSchema] = []
    for row in analysis_rows:
        anomaly_score = 1.0 - row.normality_score
        flags_raw = json.loads(row.suspicious_flags) if row.suspicious_flags else []
        events = []
        for f in flags_raw:
            if isinstance(f, dict):
                events.append(AnomalyEventSchema(type=f["type"], timestamp=f.get("timestamp", ""), detail=f.get("detail", "")))
            else:
                events.append(AnomalyEventSchema(type=str(f), timestamp="", detail=""))
        individual.append(
            IndividualResultSchema(
                student_id=row.student_id,
                anomaly_score=anomaly_score,
                events=events,
            )
        )

    # Load similarity pairs
    sp_result = await db.execute(
        select(SimilarityPair).where(SimilarityPair.exam_id == exam_id)
    )
    pair_rows = sp_result.scalars().all()

    nodes: list[int] = list({row.student_id for row in analysis_rows})
    edges: list[SimilarityEdgeSchema] = []
    for row in pair_rows:
        details_dict: dict = json.loads(row.details) if row.details else {}
        edges.append(
            SimilarityEdgeSchema(
                student_a=row.student_a_id,
                student_b=row.student_b_id,
                score=row.similarity_score,
                details=details_dict,
            )
        )

    group = GroupResultSchema(nodes=nodes, edges=edges)

    # Compute suspects
    suspect_set: set[int] = set()
    for row in analysis_rows:
        anomaly_score = 1.0 - row.normality_score
        if anomaly_score > settings.SUSPECT_ANOMALY_THRESHOLD:
            suspect_set.add(row.student_id)
    for row in pair_rows:
        if row.similarity_score > settings.SUSPECT_SIMILARITY_THRESHOLD:
            suspect_set.add(row.student_a_id)
            suspect_set.add(row.student_b_id)

    return ReportResponse(
        exam_id=exam_id,
        generated_at=_now_iso(),
        individual=individual,
        group=group,
        suspects=sorted(suspect_set),
    )
