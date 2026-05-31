# TASK-032: Cohort-relative late start detection

status: done
created: 2026-05-31
updated: 2026-05-31

## Description

Replace the current late start detection logic with a cohort-relative approach.
Currently `_detect_late_start` compares a student's first commit against
`exam_start + (duration × late_start_fraction)` — an arbitrary scheduled time.

New approach: compute the **median first-commit timestamp** across all students
in the exam. Flag a student if their first commit is more than
`late_start_threshold_minutes` (default 15) after that cohort median.

This catches students who waited for peers to finish before submitting,
without depending on the accuracy of the official exam schedule.

## Plan

### 1. `analysis_individual.py` — change `_detect_late_start` signature

Old:
```python
def _detect_late_start(
    sorted_commits, exam_start, exam_duration_minutes, late_start_fraction
)
```

New:
```python
def _detect_late_start(
    sorted_commits: list[CommitRecord],
    cohort_median_start: datetime,
    late_start_threshold_minutes: int,
) -> list[AnomalyEvent]:
```

Logic: flag if `first_commit_dt >= cohort_median_start + timedelta(minutes=late_start_threshold_minutes)`.

Event detail: `"First commit Xm Ys after cohort median start"` (drop exam-duration % phrasing).

### 2. `analysis_individual.py` — change `analyze_student` signature

Remove params: `exam_start`, `exam_duration_minutes`, `late_start_fraction`.
Add params:
- `cohort_first_commits: list[str]`  — ISO timestamps, one per student in cohort
- `late_start_threshold_minutes: int = 15`

Inside `analyze_student`:
1. Parse all `cohort_first_commits` to datetimes.
2. Sort and pick median (`cohort_first_commits[n // 2]`).
3. Pass `cohort_median_start` and `late_start_threshold_minutes` to `_detect_late_start`.

If `cohort_first_commits` is empty, skip late start detection (return no event).

### 3. `config.py`

- Remove `LATE_START_FRACTION: float = 0.8`
- Add `LATE_START_THRESHOLD_MINUTES: int = 15`

### 4. `routers/analysis.py` — two-pass individual analysis

Before the per-student loop, collect cohort first commits:

```python
cohort_first_commits: list[str] = []
for student_id, student_commits in commits_by_student.items():
    sorted_sc = sorted(student_commits, key=lambda c: c.timestamp)
    if sorted_sc:
        cohort_first_commits.append(sorted_sc[0].timestamp)
```

Then pass `cohort_first_commits` and `settings.LATE_START_THRESHOLD_MINUTES`
to each `analyze_student` call. Remove `exam_start` and `late_start_fraction`
from that call.

The per-student `exam_start` lookup from `sessions_by_student` becomes unused —
remove it along with the `sessions_result` query and `fallback_start`.

### 5. `tests/test_services_individual.py`

- Remove `EXAM_START` constant (no longer needed).
- Update `_detect_late_start` calls to new signature.
- Update `analyze_student` calls: replace `exam_start`/`exam_duration_minutes`
  with `cohort_first_commits` list.
- Rewrite late start test cases:
  - `test_late_start_detected`: cohort median at T+0, student first commit at T+20min → flagged.
  - `test_no_late_start_early_commit`: student first commit at T+5min → not flagged.
  - `test_late_start_empty_cohort`: `cohort_first_commits=[]` → no event.
  - `test_late_start_at_boundary`: first commit exactly at threshold → not flagged (strict `>`).

## Acceptance criteria

- [ ] `_detect_late_start` uses cohort median, not `exam_start + fraction`
- [ ] `analyze_student` accepts `cohort_first_commits` list, drops `exam_start`/`late_start_fraction`
- [ ] `config.py` has `LATE_START_THRESHOLD_MINUTES = 15`, no `LATE_START_FRACTION`
- [ ] Router computes cohort first commits before per-student loop, passes to `analyze_student`
- [ ] `sessions_by_student` query removed (no longer needed)
- [ ] All existing tests pass
- [ ] New cohort-relative late start test cases added and passing

## Notes

Median chosen over mean — resistant to outliers (one student who cloned repo
hours late won't skew the baseline).

Strict `>` comparison at threshold boundary — student committing exactly at
`median + 15min` is NOT flagged.
