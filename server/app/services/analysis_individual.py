"""Individual student commit pattern analysis service.

Pure Python computation module — no FastAPI, no DB queries.
Receives plain Python objects and returns analysis results.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO 8601 string to an aware datetime (UTC)."""
    # Handle both 'Z' suffix and '+00:00' offset
    ts = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class CommitRecord:
    commit_id: str
    student_id: int
    timestamp: str        # ISO 8601
    lines_added: int
    lines_removed: int
    file_name: str
    exercise_id: str
    diff_content: str | None = None  # raw diff text for AST extraction


@dataclass
class AnomalyEvent:
    type: str    # "burst" | "late_start" | "inactivity_gap"
    timestamp: str   # when it happened (ISO 8601)
    detail: str      # human-readable description


@dataclass
class StudentAnalysisResult:
    student_id: int
    anomaly_score: float          # 0.0 (normal) to 1.0 (very suspicious)
    events: list[AnomalyEvent] = field(default_factory=list)


def _detect_bursts(
    sorted_commits: list[CommitRecord],
    burst_lines_threshold: int,
    burst_window_seconds: int,
) -> list[AnomalyEvent]:
    """Slide a window over the sorted commit timeline.

    For each commit i, accumulate lines_added for all commits j where
    timestamp[j] - timestamp[i] < burst_window_seconds.
    Fire one AnomalyEvent per detected burst window (deduplicated: once the
    window that triggered the event advances past the anchor, we move on).
    """
    events: list[AnomalyEvent] = []
    n = len(sorted_commits)
    in_burst = False  # simple dedup: don't fire repeatedly for same blob

    for i in range(n):
        anchor_dt = _parse_iso(sorted_commits[i].timestamp)
        window_lines = 0
        for j in range(i, n):
            j_dt = _parse_iso(sorted_commits[j].timestamp)
            delta = (j_dt - anchor_dt).total_seconds()
            if delta <= burst_window_seconds:
                window_lines += sorted_commits[j].lines_added
            else:
                break

        if window_lines > burst_lines_threshold:
            if not in_burst:
                events.append(AnomalyEvent(
                    type="burst",
                    timestamp=sorted_commits[i].timestamp,
                    detail=(
                        f"{window_lines} lines added within "
                        f"{burst_window_seconds}s window "
                        f"(threshold: {burst_lines_threshold})"
                    ),
                ))
            in_burst = True
        else:
            in_burst = False

    return events


def _detect_late_start(
    sorted_commits: list[CommitRecord],
    cohort_median_start: datetime,
    late_start_threshold_minutes: int,
) -> list[AnomalyEvent]:
    """Detect whether the student's first commit is after the cohort-relative threshold."""
    from datetime import timedelta

    if not sorted_commits:
        return []

    threshold_dt = cohort_median_start + timedelta(minutes=late_start_threshold_minutes)
    first_commit = sorted_commits[0]
    first_dt = _parse_iso(first_commit.timestamp)

    if first_dt > threshold_dt:
        delta_seconds = (first_dt - cohort_median_start).total_seconds()
        minutes = int(delta_seconds // 60)
        seconds = int(delta_seconds % 60)
        return [AnomalyEvent(
            type="late_start",
            timestamp=first_commit.timestamp,
            detail=f"First commit {minutes}m {seconds}s after cohort median start",
        )]

    return []


def _detect_inactivity_gaps(
    sorted_commits: list[CommitRecord],
    inactivity_gap_minutes: int,
    burst_lines_threshold: int,
    burst_window_seconds: int,
) -> list[AnomalyEvent]:
    """Find consecutive pairs of commits with a gap > inactivity_gap_minutes.

    A gap is flagged only when it is followed by a burst (the lines_added in
    the window immediately after the gap exceed burst_lines_threshold).
    """
    from datetime import timedelta

    events: list[AnomalyEvent] = []
    n = len(sorted_commits)
    gap_threshold_seconds = inactivity_gap_minutes * 60

    for i in range(n - 1):
        t_before = _parse_iso(sorted_commits[i].timestamp)
        t_after = _parse_iso(sorted_commits[i + 1].timestamp)
        gap_seconds = (t_after - t_before).total_seconds()

        if gap_seconds > gap_threshold_seconds:
            # Check whether what follows the gap is a burst
            window_lines = 0
            for j in range(i + 1, n):
                j_dt = _parse_iso(sorted_commits[j].timestamp)
                delta = (j_dt - t_after).total_seconds()
                if delta <= burst_window_seconds:
                    window_lines += sorted_commits[j].lines_added
                else:
                    break

            if window_lines > 0:
                gap_minutes = gap_seconds / 60.0
                events.append(AnomalyEvent(
                    type="inactivity_gap",
                    timestamp=sorted_commits[i + 1].timestamp,
                    detail=(
                        f"{gap_minutes:.1f}-minute inactivity gap followed by "
                        f"{window_lines} lines added"
                    ),
                ))

    return events


def analyze_student(
    student_id: int,
    commits: list[CommitRecord],
    cohort_first_commits: list[str] | None = None,
    burst_lines_threshold: int = 200,
    burst_window_seconds: int = 60,
    late_start_threshold_minutes: int = 15,
    inactivity_gap_minutes: int = 15,
) -> StudentAnalysisResult:
    """Analyse a single student's commit pattern and return an anomaly score.

    Parameters
    ----------
    student_id:
        The student being analysed.
    commits:
        All CommitRecord objects belonging to this student for the exam.
    cohort_first_commits:
        ISO 8601 timestamps of each cohort student's first commit. Used to
        compute the median start for late-start detection. Pass [] or None to
        skip late-start detection.
    burst_lines_threshold:
        Lines-added threshold that triggers a burst event (default 200).
    burst_window_seconds:
        Time window in seconds used when measuring bursts (default 60).
    late_start_threshold_minutes:
        Minutes after cohort median start before a student is flagged (default 15).
    inactivity_gap_minutes:
        Minimum gap length (minutes) between consecutive commits that counts as
        an inactivity period (default 15).

    Returns
    -------
    StudentAnalysisResult with anomaly_score in [0.0, 1.0] and event list.
    """
    if not commits:
        return StudentAnalysisResult(student_id=student_id, anomaly_score=0.0, events=[])

    sorted_commits = sorted(commits, key=lambda c: _parse_iso(c.timestamp))

    burst_events = _detect_bursts(sorted_commits, burst_lines_threshold, burst_window_seconds)

    if cohort_first_commits:
        parsed_cohort = sorted(_parse_iso(ts) for ts in cohort_first_commits)
        cohort_median_start = parsed_cohort[len(parsed_cohort) // 2]
        late_start_events = _detect_late_start(
            sorted_commits, cohort_median_start, late_start_threshold_minutes
        )
    else:
        late_start_events = []

    gap_events = _detect_inactivity_gaps(
        sorted_commits, inactivity_gap_minutes, burst_lines_threshold, burst_window_seconds
    )

    all_events = burst_events + late_start_events + gap_events

    # --- Score formula ---
    # Bursts: +0.3 each, capped at 0.6
    burst_score = min(len(burst_events) * 0.3, 0.6)
    # Late start: +0.4
    late_score = 0.4 if late_start_events else 0.0
    # Inactivity gaps: +0.15 each, capped at 0.3
    gap_score = min(len(gap_events) * 0.15, 0.3)

    raw_score = burst_score + late_score + gap_score
    anomaly_score = max(0.0, min(1.0, raw_score))

    return StudentAnalysisResult(
        student_id=student_id,
        anomaly_score=anomaly_score,
        events=all_events,
    )
