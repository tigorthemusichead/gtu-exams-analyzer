# TASK-026: Show student emails instead of IDs in report

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
Report view currently displays raw `student_id` integers everywhere (graph node labels, anomaly scores table, suspect pairs table). Replace with student email addresses.

Backend must join `User.email` when building the report response. Frontend must render emails in all three places: D3 graph node labels, individual anomaly scores table, suspect pairs table.

## Acceptance criteria
- [ ] `exam_report_page()` in `routers/web.py` joins `User` table to resolve `student_id → email` for all `AnalysisResult` and `SimilarityPair` records
- [ ] `ReportResponse` / serialized JSON passed to template includes email alongside or instead of raw ID
- [ ] D3 graph node labels show email (or username portion) instead of `"S{id}"`
- [ ] Anomaly scores table rows show email in student column
- [ ] Suspect pairs table rows show emails for both students in pair
- [ ] Tooltips on graph nodes show full email

## Notes
- Emails live in `User` table; `AnalysisResult.student_id` and `SimilarityPair.student_a_id/student_b_id` are FKs to `User.user_id`
- Build a `{student_id: email}` lookup dict server-side and pass it in template context — avoids schema changes
- D3 node label currently: `"S" + d.id` in `report.js` line ~82
