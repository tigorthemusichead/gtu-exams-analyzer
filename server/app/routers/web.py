"""Teacher web dashboard — HTML routes served by FastAPI (TASK-017)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.dependencies import require_teacher_web
from app.models.models import AnalysisResult, Exam, User
from app.schemas.schemas import ExamResponse, ReportResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

TEMPLATES_DIR = Path(__file__).parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["web"])


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    payload: dict = Depends(require_teacher_web),
    db: AsyncSession = Depends(get_db),
):
    teacher_id = int(payload["sub"])
    result = await db.execute(select(Exam).where(Exam.teacher_id == teacher_id))
    exams = result.scalars().all()

    analyzed = []
    pending = []
    for exam in exams:
        count_result = await db.execute(
            select(func.count(AnalysisResult.result_id)).where(
                AnalysisResult.exam_id == exam.exam_id
            )
        )
        has_report = (count_result.scalar_one() or 0) > 0

        from sqlalchemy import select as sel
        from app.models.models import ExamSession
        sess_result = await db.execute(
            sel(func.count(ExamSession.session_id)).where(
                ExamSession.exam_id == exam.exam_id
            )
        )
        participant_count = sess_result.scalar_one() or 0

        exam_data = ExamResponse(
            exam_id=exam.exam_id,
            name=exam.name,
            group_number=exam.group_number,
            exam_date=exam.exam_date,
            duration_minutes=exam.duration_minutes,
            created_at=exam.created_at,
            has_report=has_report,
            participant_count=participant_count,
        )
        (analyzed if has_report else pending).append(exam_data)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"analyzed": analyzed, "pending": pending},
    )


@router.get("/exams/new", response_class=HTMLResponse)
async def exam_new_page(
    request: Request,
    payload: dict = Depends(require_teacher_web),
):
    return templates.TemplateResponse(request, "exam_new.html")


@router.get("/exams/{exam_id}", response_class=HTMLResponse)
async def exam_detail_page(
    request: Request,
    exam_id: int,
    payload: dict = Depends(require_teacher_web),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Exam).where(Exam.exam_id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        return RedirectResponse(url="/dashboard")

    count_result = await db.execute(
        select(func.count(AnalysisResult.result_id)).where(
            AnalysisResult.exam_id == exam_id
        )
    )
    has_report = (count_result.scalar_one() or 0) > 0

    from app.models.models import ExamSession
    sess_result = await db.execute(
        select(func.count(ExamSession.session_id)).where(
            ExamSession.exam_id == exam_id
        )
    )
    participant_count = sess_result.scalar_one() or 0

    exam_data = ExamResponse(
        exam_id=exam.exam_id,
        name=exam.name,
        group_number=exam.group_number,
        exam_date=exam.exam_date,
        duration_minutes=exam.duration_minutes,
        created_at=exam.created_at,
        has_report=has_report,
        participant_count=participant_count,
    )
    return templates.TemplateResponse(
        request, "exam_detail.html", {"exam": exam_data}
    )


@router.get("/exams/{exam_id}/report", response_class=HTMLResponse)
async def exam_report_page(
    request: Request,
    exam_id: int,
    payload: dict = Depends(require_teacher_web),
    db: AsyncSession = Depends(get_db),
):
    from app.routers.analysis import get_report as _get_report
    from app.models.models import SimilarityPair

    result = await db.execute(select(Exam).where(Exam.exam_id == exam_id))
    exam = result.scalar_one_or_none()
    if exam is None:
        return RedirectResponse(url="/dashboard")

    # Load analysis results
    ar_result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.exam_id == exam_id)
    )
    analysis_rows = ar_result.scalars().all()

    sp_result = await db.execute(
        select(SimilarityPair).where(SimilarityPair.exam_id == exam_id)
    )
    pair_rows = sp_result.scalars().all()

    from app.config import settings
    from app.schemas.schemas import (
        AnomalyEventSchema,
        GroupResultSchema,
        IndividualResultSchema,
        SimilarityEdgeSchema,
    )
    import json as _json

    # Build student_id → email lookup
    all_student_ids = (
        {row.student_id for row in analysis_rows}
        | {row.student_a_id for row in pair_rows}
        | {row.student_b_id for row in pair_rows}
    )
    user_result = await db.execute(
        select(User).where(User.user_id.in_(all_student_ids))
    )
    student_emails: dict[int, str] = {u.user_id: u.email for u in user_result.scalars().all()}

    individual = []
    suspect_set: set[int] = set()
    anomaly_suspect_ids: set[int] = set()
    for row in analysis_rows:
        anomaly_score = 1.0 - row.normality_score
        flags_raw = _json.loads(row.suspicious_flags) if row.suspicious_flags else []
        events = []
        for f in flags_raw:
            if isinstance(f, dict):
                events.append(AnomalyEventSchema(type=f["type"], timestamp=f.get("timestamp", ""), detail=f.get("detail", "")))
            else:
                events.append(AnomalyEventSchema(type=str(f), timestamp="", detail=""))
        individual.append(IndividualResultSchema(student_id=row.student_id, anomaly_score=anomaly_score, events=events))
        if anomaly_score > settings.SUSPECT_ANOMALY_THRESHOLD:
            suspect_set.add(row.student_id)
            anomaly_suspect_ids.add(row.student_id)

    edges = []
    for row in pair_rows:
        details_dict = _json.loads(row.details) if row.details else {}
        edges.append(SimilarityEdgeSchema(
            student_a=row.student_a_id,
            student_b=row.student_b_id,
            score=row.similarity_score,
            details=details_dict,
        ))
        if row.similarity_score > settings.SUSPECT_SIMILARITY_THRESHOLD:
            suspect_set.add(row.student_a_id)
            suspect_set.add(row.student_b_id)

    nodes = list({row.student_id for row in analysis_rows})
    group = GroupResultSchema(nodes=nodes, edges=edges)
    from app.schemas.schemas import ReportResponse as RR
    from datetime import datetime, timezone
    report = RR(
        exam_id=exam_id,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        individual=individual,
        group=group,
        suspects=sorted(suspect_set),
    )

    exam_data = ExamResponse(
        exam_id=exam.exam_id,
        name=exam.name,
        group_number=exam.group_number,
        exam_date=exam.exam_date,
        duration_minutes=exam.duration_minutes,
        created_at=exam.created_at,
        has_report=True,
        participant_count=len(nodes),
    )

    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "exam": exam_data,
            "report": report,
            "report_json": report.model_dump_json(),
            "student_emails": student_emails,
            "student_emails_json": _json.dumps({str(k): v for k, v in student_emails.items()}),
            "anomaly_suspect_ids": anomaly_suspect_ids,
        },
    )
