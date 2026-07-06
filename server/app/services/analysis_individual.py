from dataclasses import dataclass, field
from datetime import datetime, timezone


def _parse_iso(ts: str) -> datetime:
    ts = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class CommitRecord:
    commit_id: str
    student_id: int
    timestamp: str
    lines_added: int
    lines_removed: int
    file_name: str
    exercise_id: str
    diff_content: str | None = None


@dataclass
class AnomalyEvent:
    type: str
    timestamp: str
    detail: str


@dataclass
class StudentAnalysisResult:
    student_id: int
    anomaly_score: float
    events: list[AnomalyEvent] = field(default_factory=list)


def _detect_bursts(
    sorted_commits: list[CommitRecord],
    burst_lines_threshold: int,
    burst_window_seconds: int,
) -> list[AnomalyEvent]:
    events: list[AnomalyEvent] = []
    n = len(sorted_commits)
    in_burst = False

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
    from datetime import timedelta

    events: list[AnomalyEvent] = []
    n = len(sorted_commits)
    gap_threshold_seconds = inactivity_gap_minutes * 60

    for i in range(n - 1):
        t_before = _parse_iso(sorted_commits[i].timestamp)
        t_after = _parse_iso(sorted_commits[i + 1].timestamp)
        gap_seconds = (t_after - t_before).total_seconds()

        if gap_seconds > gap_threshold_seconds:
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

    burst_score = min(len(burst_events) * 0.3, 0.6)
    late_score = 0.4 if late_start_events else 0.0
    gap_score = min(len(gap_events) * 0.15, 0.3)

    raw_score = burst_score + late_score + gap_score
    anomaly_score = max(0.0, min(1.0, raw_score))

    return StudentAnalysisResult(
        student_id=student_id,
        anomaly_score=anomaly_score,
        events=all_events,
    )
