# TASK-009: Report generation endpoint

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Teacher endpoints to trigger analysis and retrieve report.

**Trigger analysis** `POST /analysis/{exam_id}`:
- Auth: teacher JWT, must own exam
- Runs TASK-007 + TASK-008 analysis, persists results
- Returns 202 Accepted (async) or 200 with results (sync for MVP)

**Get report** `GET /reports/{exam_id}`:
- Auth: teacher JWT, must own exam
- Returns full report JSON:
  ```json
  {
    "exam_id": "...",
    "generated_at": "...",
    "individual": [
      {"student_id": "...", "anomaly_score": 0.0, "events": [...]}
    ],
    "group": {
      "nodes": [...],
      "edges": [{"student_a": "...", "student_b": "...", "score": 0.0, "details": {}}]
    },
    "suspects": ["student_id", ...]
  }
  ```
- `suspects` = students where anomaly_score > threshold OR involved in edge with score > threshold

## Acceptance criteria
- [x] `POST /analysis/{exam_id}` triggers both analyses and persists report
- [x] `GET /reports/{exam_id}` returns persisted report
- [x] 404 if report not yet generated
- [x] 403 if teacher doesn't own the exam
- [x] `suspects` list computed correctly from thresholds

## Notes
Blocked by TASK-007 and TASK-008.
