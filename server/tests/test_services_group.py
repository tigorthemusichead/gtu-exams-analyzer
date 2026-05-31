"""Unit tests for analysis_group service."""

import pytest
from app.services.analysis_individual import CommitRecord
from app.services.analysis_group import (
    analyze_group,
    _compute_cosine_scores,
    _compute_structural_scores,
    _compute_sequential_scores,
    _commits_content_similar,
    _extract_ast_tokens,
)


def make_commit(student_id: int, ts: str, exercise_id: str = "ex1",
                file_name: str = "solution.py", lines_added: int = 10,
                diff_content: str | None = None) -> CommitRecord:
    return CommitRecord(
        commit_id=f"{student_id}-{ts}",
        student_id=student_id,
        timestamp=ts,
        lines_added=lines_added,
        lines_removed=0,
        file_name=file_name,
        exercise_id=exercise_id,
        diff_content=diff_content,
    )


# --- AST extraction ---

def test_extract_ast_tokens_function_names():
    diff = "+def solve_problem():\n+    result = 42\n+    return result\n"
    tokens = _extract_ast_tokens(diff)
    assert "solve_problem" in tokens
    assert "result" in tokens


def test_extract_ast_tokens_class_names():
    diff = "+class Solution:\n+    def method(self):\n+        pass\n"
    tokens = _extract_ast_tokens(diff)
    assert "Solution" in tokens
    assert "method" in tokens


def test_extract_ast_tokens_syntax_error_fallback():
    # Invalid python should return empty set (no exception)
    tokens = _extract_ast_tokens("+def (:\n+    pass\n")
    assert isinstance(tokens, set)


def test_extract_ast_tokens_empty_diff():
    tokens = _extract_ast_tokens("")
    assert tokens == set()


def test_extract_ast_tokens_non_added_lines_ignored():
    diff = "-def old():\n-    pass\n+def new_func():\n+    pass\n"
    tokens = _extract_ast_tokens(diff)
    assert "new_func" in tokens
    assert "old" not in tokens


# --- Cosine scores ---

def test_cosine_scores_identical_students():
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="a.py")],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1", file_name="a.py")],
    }
    scores = _compute_cosine_scores([1, 2], commits)
    assert scores[(1, 2)] > 0.8


def test_cosine_scores_different_students():
    """Students with completely different exercises/files should score lower than identical."""
    identical_commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="a.py")],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1", file_name="a.py")],
    }
    different_commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="a.py")],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex9", file_name="z.py")],
    }
    score_identical = _compute_cosine_scores([1, 2], identical_commits)[(1, 2)]
    score_different = _compute_cosine_scores([1, 2], different_commits)[(1, 2)]
    assert score_identical >= score_different


def test_cosine_scores_empty_documents():
    commits = {
        1: [],
        2: [],
    }
    scores = _compute_cosine_scores([1, 2], commits)
    assert scores[(1, 2)] == 0.0


def test_cosine_scores_single_student():
    commits = {1: [make_commit(1, "2026-06-01T08:05:00Z")]}
    scores = _compute_cosine_scores([1], commits)
    assert scores == {}


# --- Structural scores ---

def test_structural_scores_identical_file_names():
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="solution.py", exercise_id="ex1")],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="solution.py", exercise_id="ex1")],
    }
    scores = _compute_structural_scores([1, 2], commits)
    assert scores[(1, 2)] == 1.0


def test_structural_scores_with_ast():
    diff_a = "+def compute(x):\n+    total = x * 2\n+    return total\n"
    diff_b = "+def compute(x):\n+    total = x * 2\n+    return total\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=diff_a)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", diff_content=diff_b)],
    }
    scores = _compute_structural_scores([1, 2], commits)
    assert scores[(1, 2)] > 0.5


def test_structural_scores_non_python_no_crash():
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="main.java", diff_content="+void main(){}")],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="main.java", diff_content="+void main(){}")],
    }
    scores = _compute_structural_scores([1, 2], commits)
    assert isinstance(scores[(1, 2)], float)


# --- Sequential scores ---

_SIMILAR_DIFF = (
    "+def compute(value):\n"
    "+    result = value * 2\n"
    "+    return result\n"
)

_DISSIMILAR_DIFF = (
    "+class DataProcessor:\n"
    "+    def run(self, dataset):\n"
    "+        return dataset\n"
)


def test_sequential_scores_simultaneous_commits():
    """Timing overlap + content similarity → score 1.0."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=_SIMILAR_DIFF)],
        2: [make_commit(2, "2026-06-01T08:05:10Z", diff_content=_SIMILAR_DIFF)],  # 10s apart
    }
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    score, matches = result[(1, 2)]
    assert score == 1.0
    assert len(matches) == 1


def test_sequential_scores_far_apart():
    """No timing overlap → score 0 regardless of content."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=_SIMILAR_DIFF)],
        2: [make_commit(2, "2026-06-01T09:30:00Z", diff_content=_SIMILAR_DIFF)],  # 85 min apart
    }
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


def test_sequential_scores_empty_commits():
    commits = {1: [], 2: [make_commit(2, "2026-06-01T08:05:00Z")]}
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


def test_sequential_scores_timing_overlap_low_content_similarity():
    """Timing overlap but dissimilar content → score 0 (no false positive)."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=_SIMILAR_DIFF)],
        2: [make_commit(2, "2026-06-01T08:05:30Z", diff_content=_DISSIMILAR_DIFF)],  # 30s apart
    }
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


def test_sequential_scores_no_diff_content():
    """Commits with None diff_content cannot satisfy content check → score 0."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z")],   # diff_content=None
        2: [make_commit(2, "2026-06-01T08:05:10Z")],   # diff_content=None
    }
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


def test_sequential_scores_matched_pair_fields():
    """matched_pairs dicts include who_first, exercise_id, file_name."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex2", file_name="sort.py",
                        diff_content=_SIMILAR_DIFF)],
        2: [make_commit(2, "2026-06-01T08:05:30Z", exercise_id="ex2", file_name="sort.py",
                        diff_content=_SIMILAR_DIFF)],
    }
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    _, matches = result[(1, 2)]
    assert len(matches) == 1
    m = matches[0]
    assert "who_first" in m
    assert "exercise_id" in m
    assert "file_name" in m
    assert m["exercise_id"] == "ex2"
    assert m["file_name"] == "sort.py"


def test_sequential_scores_who_first_a_before_b():
    """who_first = 'a' when student A commits before B."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:00:00Z", diff_content=_SIMILAR_DIFF)],
        2: [make_commit(2, "2026-06-01T08:03:00Z", diff_content=_SIMILAR_DIFF)],  # 3 min later
    }
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    _, matches = result[(1, 2)]
    assert matches[0]["who_first"] == "a"


def test_sequential_scores_who_first_b_before_a():
    """who_first = 'b' when student B commits before A."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=_SIMILAR_DIFF)],
        2: [make_commit(2, "2026-06-01T08:02:00Z", diff_content=_SIMILAR_DIFF)],  # 3 min earlier
    }
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    _, matches = result[(1, 2)]
    assert matches[0]["who_first"] == "b"


def test_sequential_scores_who_first_same_second():
    """who_first = 'a' when both commit at same second (ta == tb → ta <= tb)."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=_SIMILAR_DIFF)],
        2: [make_commit(2, "2026-06-01T08:05:00Z", diff_content=_SIMILAR_DIFF)],
    }
    result = _compute_sequential_scores(
        [1, 2], commits,
        sequential_window_seconds=300,
        content_threshold=0.4,
        min_tokens=3,
    )
    _, matches = result[(1, 2)]
    assert matches[0]["who_first"] == "a"


# --- End-to-end analyze_group ---

def test_analyze_group_less_than_two_students():
    result = analyze_group({1: [make_commit(1, "2026-06-01T08:05:00Z")]})
    assert result.nodes == [1]
    assert result.edges == []


def test_analyze_group_all_identical_commits():
    same_commits = lambda sid: [
        make_commit(sid, "2026-06-01T08:05:00Z", exercise_id="ex1",
                    file_name="sol.py", lines_added=100)
    ]
    commits = {1: same_commits(1), 2: same_commits(2)}
    result = analyze_group(commits, edge_threshold=0.5)
    assert len(result.nodes) == 2
    # With identical data, score should be high
    assert any(e.score >= 0.5 for e in result.edges)


def test_analyze_group_edge_threshold_zero_returns_all():
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z")],
        2: [make_commit(2, "2026-06-01T09:00:00Z", exercise_id="ex99", file_name="z.py")],
    }
    result = analyze_group(commits, edge_threshold=0.0)
    assert len(result.edges) == 1  # one pair exists


def test_analyze_group_weights_sum_to_correct():
    """Verify combined score uses provided weights."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z")],
        2: [make_commit(2, "2026-06-01T08:05:30Z")],
    }
    result = analyze_group(
        commits,
        weight_cosine=0.5,
        weight_structural=0.3,
        weight_sequential=0.2,
        edge_threshold=0.0,
    )
    for edge in result.edges:
        expected = (
            0.5 * edge.details["cosine"]
            + 0.3 * edge.details["structural"]
            + 0.2 * edge.details["sequential"]
        )
        assert abs(edge.score - expected) < 1e-9
