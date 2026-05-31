"""Unit tests for analysis_individual service."""

import pytest
from datetime import datetime, timedelta, timezone

from app.services.analysis_individual import (
    CommitRecord,
    analyze_student,
    _detect_bursts,
    _detect_late_start,
    _detect_inactivity_gaps,
)


def make_commit(i: int, ts: str, lines_added: int = 10, lines_removed: int = 0) -> CommitRecord:
    return CommitRecord(
        commit_id=f"c{i}",
        student_id=1,
        timestamp=ts,
        lines_added=lines_added,
        lines_removed=lines_removed,
        file_name="solution.py",
        exercise_id="ex1",
    )


# --- Empty commit list ---

def test_empty_commits_score_zero():
    result = analyze_student(student_id=1, commits=[])
    assert result.anomaly_score == 0.0
    assert result.events == []


# --- Burst detection ---

def test_detect_burst_above_threshold():
    commits = [
        make_commit(1, "2026-06-01T08:05:00Z", lines_added=100),
        make_commit(2, "2026-06-01T08:05:30Z", lines_added=150),
    ]
    events = _detect_bursts(commits, burst_lines_threshold=200, burst_window_seconds=60)
    assert len(events) == 1
    assert events[0].type == "burst"


def test_no_burst_below_threshold():
    commits = [
        make_commit(1, "2026-06-01T08:05:00Z", lines_added=50),
        make_commit(2, "2026-06-01T08:05:30Z", lines_added=50),
    ]
    events = _detect_bursts(commits, burst_lines_threshold=200, burst_window_seconds=60)
    assert events == []


def test_burst_deduplication():
    """Adjacent bursting windows should emit only one event per blob."""
    commits = [
        make_commit(1, "2026-06-01T08:05:00Z", lines_added=150),
        make_commit(2, "2026-06-01T08:05:10Z", lines_added=100),
        make_commit(3, "2026-06-01T08:05:20Z", lines_added=100),
    ]
    events = _detect_bursts(commits, burst_lines_threshold=200, burst_window_seconds=60)
    assert len(events) == 1


# --- Late start detection ---

def test_late_start_detected():
    # Cohort median at T+0, student first commit at T+20min → flagged (threshold 15min)
    median_dt = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
    late_ts = "2026-06-01T08:20:00Z"
    commits = [make_commit(1, late_ts)]
    events = _detect_late_start(commits, median_dt, late_start_threshold_minutes=15)
    assert len(events) == 1
    assert events[0].type == "late_start"


def test_no_late_start_early_commit():
    # Student first commit at T+5min → not flagged
    median_dt = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
    early_ts = "2026-06-01T08:05:00Z"
    commits = [make_commit(1, early_ts)]
    events = _detect_late_start(commits, median_dt, late_start_threshold_minutes=15)
    assert events == []


def test_late_start_empty_commits():
    median_dt = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
    events = _detect_late_start([], median_dt, late_start_threshold_minutes=15)
    assert events == []


def test_late_start_empty_cohort():
    # cohort_first_commits=[] → no late start event
    commits = [make_commit(1, "2026-06-01T08:20:00Z")]
    result = analyze_student(1, commits, cohort_first_commits=[])
    late_events = [e for e in result.events if e.type == "late_start"]
    assert late_events == []


def test_late_start_at_boundary():
    # First commit exactly at median + threshold → NOT flagged (strict >)
    median_dt = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
    boundary_ts = "2026-06-01T08:15:00Z"  # exactly 15 minutes after median
    commits = [make_commit(1, boundary_ts)]
    events = _detect_late_start(commits, median_dt, late_start_threshold_minutes=15)
    assert events == []


# --- Inactivity gap detection ---

def test_inactivity_gap_with_burst():
    commits = [
        make_commit(1, "2026-06-01T08:05:00Z", lines_added=5),
        # 20-minute gap
        make_commit(2, "2026-06-01T08:25:00Z", lines_added=10),
    ]
    events = _detect_inactivity_gaps(commits, inactivity_gap_minutes=15, burst_lines_threshold=5, burst_window_seconds=60)
    assert len(events) == 1
    assert events[0].type == "inactivity_gap"


def test_no_gap_short_interval():
    commits = [
        make_commit(1, "2026-06-01T08:05:00Z", lines_added=5),
        make_commit(2, "2026-06-01T08:10:00Z", lines_added=10),
    ]
    events = _detect_inactivity_gaps(commits, inactivity_gap_minutes=15, burst_lines_threshold=5, burst_window_seconds=60)
    assert events == []


# --- Composite scoring ---

def test_anomaly_score_capped_at_1():
    # Many bursts + late start = should not exceed 1.0
    commits = [
        make_commit(1, "2026-06-01T08:10:00Z", lines_added=300),
        make_commit(2, "2026-06-01T08:10:30Z", lines_added=300),
        make_commit(3, "2026-06-01T08:11:00Z", lines_added=300),
        make_commit(4, "2026-06-01T09:10:00Z", lines_added=300),
    ]
    # Cohort median at 08:00 → last commit flagged as late start
    result = analyze_student(1, commits, cohort_first_commits=["2026-06-01T08:00:00Z"])
    assert 0.0 <= result.anomaly_score <= 1.0


def test_single_student_no_crash():
    commits = [make_commit(1, "2026-06-01T08:05:00Z")]
    result = analyze_student(1, commits)
    assert result.student_id == 1
