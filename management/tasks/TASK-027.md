# TASK-027: Individual anomaly detail modal on row click

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
Clicking a row in the anomaly scores table should open a modal (or detail page) showing the full breakdown of suspicious patterns detected for that student.

The `AnalysisResult.suspicious_flags` column stores a JSON array of flag objects from `analysis_individual.py`. Surface this data in a readable way per student.

## Acceptance criteria
- [ ] Each row in the anomaly scores table is clickable (cursor: pointer)
- [ ] Clicking a row opens a modal with student identifier (email after TASK-026) and their anomaly score
- [ ] Modal lists each suspicious flag with: flag type (burst / late_start / inactivity_gap), severity or description, and relevant timestamps/values
- [ ] Modal has a close button and closes on backdrop click or Escape key
- [ ] Data comes from `suspicious_flags` JSON already embedded in the report payload — no extra API call needed
- [ ] If no flags, modal shows "No suspicious patterns detected"

## Notes
- `AnalysisResult.suspicious_flags` stores JSON string; parsed to list of dicts when building report
- Schema in `analysis_individual.py`: each flag has at minimum a `type` field; inspect actual structure to map fields to human-readable labels
- Reuse or extend existing modal pattern already present in `report.html` (edge detail modal)
