# TASK-007: Individual student commit pattern analysis

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Analysis service that evaluates normality of a single student's commit sequence.

Patterns to detect:
1. **Burst anomaly**: large lines_added spike in implausibly short time window (configurable threshold, e.g. >200 lines in <60s)
2. **Late start anomaly**: student makes no commits in first X% of exam duration, then submits large volume near end
3. **Inactivity gaps**: long periods of zero activity followed by sudden commit bursts

Output per student: `anomaly_score` (float 0–1) + list of detected anomaly events with timestamps.

Triggered by teacher via `POST /analysis/{exam_id}` (see TASK-009).

## Acceptance criteria
- [x] Burst anomaly detected and scored correctly on synthetic test data
- [x] Late start anomaly detected when student starts in last 20% of exam window
- [x] Output schema: `{student_id, anomaly_score, events: [{type, timestamp, detail}]}`
- [x] Thresholds configurable via server config/env vars

## Notes
Blocked by TASK-006. Pure Python computation, no ML deps needed for MVP.
