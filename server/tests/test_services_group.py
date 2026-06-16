"""Unit tests for analysis_group service."""

import pytest
from app.services.analysis_individual import CommitRecord
from app.services.analysis_group import (
    analyze_group,
    _best_match_pairs,
    _compute_cosine_scores,
    _compute_structural_scores,
    _compute_sequential_scores,
    _commits_content_similar,
    _extract_ast_tokens,
    _group_commits_by_file,
    _extract_file_tokens,
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


# --- _group_commits_by_file ---

def test_group_commits_by_file_groups_correctly():
    commits = [
        make_commit(1, "2026-06-01T08:00:00Z", exercise_id="ex1", file_name="a.py"),
        make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="a.py"),
        make_commit(1, "2026-06-01T08:10:00Z", exercise_id="ex1", file_name="b.py"),
        make_commit(1, "2026-06-01T08:15:00Z", exercise_id="ex2", file_name="a.py"),
    ]
    groups = _group_commits_by_file(commits)
    assert len(groups) == 3
    assert len(groups[("ex1", "a.py")]) == 2
    assert len(groups[("ex1", "b.py")]) == 1
    assert len(groups[("ex2", "a.py")]) == 1


def test_group_commits_by_file_empty():
    assert _group_commits_by_file([]) == {}


# --- _extract_file_tokens ---

def test_extract_file_tokens_union_across_commits():
    diff_a = "+def func_alpha(x):\n+    return x\n"
    diff_b = "+def func_beta(y):\n+    return y\n"
    commits = [
        make_commit(1, "2026-06-01T08:00:00Z", diff_content=diff_a),
        make_commit(1, "2026-06-01T08:05:00Z", diff_content=diff_b),
    ]
    tokens = _extract_file_tokens(commits)
    assert "func_alpha" in tokens
    assert "func_beta" in tokens


def test_extract_file_tokens_no_diff_content():
    commits = [make_commit(1, "2026-06-01T08:00:00Z")]
    assert _extract_file_tokens(commits) == set()


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


_COSINE_DIFF = (
    "+def solve(items):\n"
    "+    total = sum(items)\n"
    "+    result = total / len(items)\n"
    "+    return result\n"
)

_COSINE_DIFF_B = (
    "+class DataLoader:\n"
    "+    def load(self, path):\n"
    "+        return open(path).read()\n"
)


# --- Cosine scores ---

def test_cosine_scores_return_type():
    """_compute_cosine_scores returns (float, list[dict]) per pair."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="a.py",
                        diff_content=_COSINE_DIFF)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1", file_name="a.py",
                        diff_content=_COSINE_DIFF)],
    }
    result = _compute_cosine_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert isinstance(score, float)
    assert isinstance(matches, list)


def test_cosine_scores_identical_students():
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="a.py",
                        diff_content=_COSINE_DIFF)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1", file_name="a.py",
                        diff_content=_COSINE_DIFF)],
    }
    result = _compute_cosine_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert score > 0.8
    assert len(matches) == 1
    assert matches[0]["exercise_id"] == "ex1"
    assert matches[0]["file_name"] == "a.py"
    assert "snippet_a" in matches[0]
    assert "snippet_b" in matches[0]


def test_cosine_scores_different_files_no_overlap():
    """Students working on different files → no shared file keys → score 0."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="a.py",
                        diff_content=_COSINE_DIFF)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex9", file_name="z.py",
                        diff_content=_COSINE_DIFF_B)],
    }
    result = _compute_cosine_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


def test_cosine_scores_no_diff_content():
    """Commits without diff_content produce empty docs → score 0."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="a.py")],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1", file_name="a.py")],
    }
    result = _compute_cosine_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


def test_cosine_scores_empty_commits():
    commits = {1: [], 2: []}
    result = _compute_cosine_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


def test_cosine_scores_single_student():
    commits = {1: [make_commit(1, "2026-06-01T08:05:00Z")]}
    result = _compute_cosine_scores([1], commits)
    assert result == {}


def test_cosine_scores_matches_sorted_by_similarity_desc():
    """Multiple shared files: matches sorted by similarity descending."""
    diff_identical = "+def func(x):\n+    return x * 2\n"
    diff_unique_a = "+def alpha_unique_function_only_in_a():\n+    pass\n" * 5
    diff_unique_b = "+def beta_unique_function_only_in_b():\n+    pass\n" * 5
    commits = {
        1: [
            make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="same.py",
                        diff_content=diff_identical),
            make_commit(1, "2026-06-01T08:10:00Z", exercise_id="ex1", file_name="diff.py",
                        diff_content=diff_unique_a),
        ],
        2: [
            make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1", file_name="same.py",
                        diff_content=diff_identical),
            make_commit(2, "2026-06-01T08:11:00Z", exercise_id="ex1", file_name="diff.py",
                        diff_content=diff_unique_b),
        ],
    }
    result = _compute_cosine_scores([1, 2], commits)
    _, matches = result[(1, 2)]
    assert len(matches) == 2
    assert matches[0]["similarity"] >= matches[1]["similarity"]


# --- Structural scores ---

def test_structural_scores_return_type():
    """_compute_structural_scores returns (float, list[dict]) per pair."""
    diff = "+def compute(x):\n+    total = x * 2\n+    return total\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert isinstance(score, float)
    assert isinstance(matches, list)


def test_structural_scores_no_diffs_returns_zero():
    """Commits without diff_content have no AST tokens → score 0, empty matches."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="solution.py", exercise_id="ex1")],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="solution.py", exercise_id="ex1")],
    }
    result = _compute_structural_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


def test_structural_scores_with_ast():
    diff_a = "+def compute(value, factor):\n+    total = value * factor\n+    result = total + value\n+    return result\n"
    diff_b = "+def compute(value, factor):\n+    total = value * factor\n+    result = total + value\n+    return result\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=diff_a)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", diff_content=diff_b)],
    }
    result = _compute_structural_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert score > 0.5
    assert len(matches) == 1
    assert "shared_tokens" in matches[0]
    assert "tokens_a" in matches[0]
    assert "tokens_b" in matches[0]


def test_structural_scores_match_fields():
    diff = "+def solve(items):\n+    result = sum(items)\n+    return result\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="sol.py",
                        diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1", file_name="sol.py",
                        diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits)
    _, matches = result[(1, 2)]
    assert len(matches) == 1
    m = matches[0]
    assert m["exercise_id"] == "ex1"
    assert m["file_name"] == "sol.py"
    assert "solve" in m["shared_tokens"]
    assert sorted(m["shared_tokens"]) == m["shared_tokens"]


def test_structural_scores_shared_tokens_subset():
    diff_a = "+def compute(value, factor):\n+    total = value * factor\n+    grand = total + factor\n+    return grand\n"
    diff_b = "+def compute(value, factor):\n+    result = value + factor\n+    outcome = result * value\n+    return outcome\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=diff_a)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", diff_content=diff_b)],
    }
    result = _compute_structural_scores([1, 2], commits)
    _, matches = result[(1, 2)]
    assert len(matches) == 1
    m = matches[0]
    assert "compute" in m["shared_tokens"]
    # shared_tokens must be subset of intersection of both token sets
    assert set(m["shared_tokens"]).issubset(set(m["tokens_a"]) & set(m["tokens_b"]))


def test_structural_scores_non_python_no_crash():
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="main.java", diff_content="+void main(){}")],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="main.java", diff_content="+void main(){}")],
    }
    result = _compute_structural_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert isinstance(score, float)
    assert isinstance(matches, list)


def test_structural_scores_below_min_tokens_skipped():
    """Files with < min_tokens AST tokens on either side are skipped."""
    diff = "+def fn():\n+    pass\n"  # only 'fn' token after filtering
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=5)
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


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


# --- Non-Python AST extraction (tree-sitter) ---

def test_extract_ast_tokens_c_function():
    diff = "+int add(int x, int y) {\n+    int result = x + y;\n+    return result;\n+}\n"
    tokens = _extract_ast_tokens(diff, "solution.c")
    assert "add" in tokens
    assert "result" in tokens


def test_extract_ast_tokens_c_struct():
    diff = "+struct Node {\n+    int value;\n+    struct Node* next;\n+};\n"
    tokens = _extract_ast_tokens(diff, "list.h")
    assert "Node" in tokens
    assert "value" in tokens


def test_extract_ast_tokens_cpp_class():
    diff = "+class Solution {\n+public:\n+    int solve(int n) { return n * 2; }\n+};\n"
    tokens = _extract_ast_tokens(diff, "main.cpp")
    assert "Solution" in tokens
    assert "solve" in tokens


def test_extract_ast_tokens_cpp_hpp():
    diff = "+class MyProcessor {\n+    void process(int data) {}\n+};\n"
    tokens = _extract_ast_tokens(diff, "processor.hpp")
    assert "MyProcessor" in tokens
    assert "process" in tokens


def test_extract_ast_tokens_csharp_class():
    diff = "+class Student {\n+    public int GetScore() { return 100; }\n+    public string Name { get; set; }\n+}\n"
    tokens = _extract_ast_tokens(diff, "Student.cs")
    assert "Student" in tokens
    assert "GetScore" in tokens


def test_extract_ast_tokens_java_class():
    diff = "+public class Solution {\n+    private int value;\n+    public int solve() { return value; }\n+}\n"
    tokens = _extract_ast_tokens(diff, "Solution.java")
    assert "Solution" in tokens
    assert "solve" in tokens


def test_extract_ast_tokens_java_method_params():
    diff = "+public int compute(int input, int factor) {\n+    return input * factor;\n+}\n"
    tokens = _extract_ast_tokens(diff, "Main.java")
    assert "compute" in tokens
    assert "input" in tokens


def test_extract_ast_tokens_javascript_function():
    diff = "+function computeAnswer(input) {\n+    const result = input * 2;\n+    return result;\n+}\n"
    tokens = _extract_ast_tokens(diff, "main.js")
    assert "computeAnswer" in tokens
    assert "result" in tokens


def test_extract_ast_tokens_javascript_class():
    diff = "+class Calculator {\n+    add(x, y) { return x + y; }\n+}\n"
    tokens = _extract_ast_tokens(diff, "calc.js")
    assert "Calculator" in tokens


def test_extract_ast_tokens_mjs_extension():
    diff = "+function fetchData(url) {\n+    const response = fetch(url);\n+    return response;\n+}\n"
    tokens = _extract_ast_tokens(diff, "utils.mjs")
    assert "fetchData" in tokens


def test_extract_ast_tokens_typescript_function():
    diff = "+function processData(items: string[]): number {\n+    const count = items.length;\n+    return count;\n+}\n"
    tokens = _extract_ast_tokens(diff, "utils.ts")
    assert "processData" in tokens
    assert "count" in tokens


def test_extract_ast_tokens_treesitter_syntax_error_no_crash():
    """Malformed code must not crash — return a set (possibly empty)."""
    diff = "+int {{{{ broken syntax\n+void @#$\n"
    for filename in ["x.c", "x.cpp", "x.cs", "x.java", "x.js", "x.ts"]:
        tokens = _extract_ast_tokens(diff, filename)
        assert isinstance(tokens, set), f"Expected set for {filename}"


def test_extract_ast_tokens_empty_diff_non_python():
    for filename in ["x.c", "x.java", "x.js"]:
        tokens = _extract_ast_tokens("", filename)
        assert isinstance(tokens, set)


# --- Structural scores for non-Python languages ---

def test_structural_scores_identical_c_code():
    diff = "+int add(int x, int y) {\n+    int result = x + y;\n+    return result;\n+}\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="sol.c", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="sol.c", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=2)
    score, _ = result[(1, 2)]
    assert score > 0.5


def test_structural_scores_unrelated_c_code_lower_than_identical():
    diff_a = "+int addValues(int alpha, int beta) {\n+    int result = alpha + beta;\n+    return result;\n+}\n"
    diff_b = "+void printOutput(char* message, int count) {\n+    printf(message);\n+    int total = count * 2;\n+}\n"
    commits_identical = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="sol.c", diff_content=diff_a)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="sol.c", diff_content=diff_a)],
    }
    commits_different = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="sol.c", diff_content=diff_a)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="sol.c", diff_content=diff_b)],
    }
    score_identical, _ = _compute_structural_scores([1, 2], commits_identical, min_tokens=2)[(1, 2)]
    score_different, _ = _compute_structural_scores([1, 2], commits_different, min_tokens=2)[(1, 2)]
    assert score_identical > score_different


def test_structural_scores_identical_java_code():
    diff = "+public class Solution {\n+    public int solve() { return 42; }\n+}\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="Solution.java", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="Solution.java", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=2)
    score, _ = result[(1, 2)]
    assert score > 0.5


def test_structural_scores_identical_javascript_code():
    diff = "+function computeAnswer(input) {\n+    const result = input * 2;\n+    return result;\n+}\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="main.js", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="main.js", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=2)
    score, _ = result[(1, 2)]
    assert score > 0.5


def test_structural_scores_identical_typescript_code():
    diff = "+function processData(items: string[]): number {\n+    const count = items.length;\n+    return count;\n+}\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="utils.ts", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="utils.ts", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=2)
    score, _ = result[(1, 2)]
    assert score > 0.5


def test_structural_scores_identical_cpp_code():
    diff = "+class Solution {\n+public:\n+    int solve(int n) { return n * 2; }\n+};\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="sol.cpp", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="sol.cpp", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=2)
    score, _ = result[(1, 2)]
    assert score > 0.5


def test_structural_scores_identical_csharp_code():
    diff = "+class Student {\n+    public int GetScore() { return 100; }\n+}\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", file_name="Student.cs", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", file_name="Student.cs", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=2)
    score, _ = result[(1, 2)]
    assert score > 0.5


# --- _best_match_pairs ---

def test_best_match_pairs_empty():
    assert _best_match_pairs({}) == []


def test_best_match_pairs_single_above_threshold():
    sims = {("a.py", "b.py"): 0.8}
    result = _best_match_pairs(sims, threshold=0.25)
    assert result == [("a.py", "b.py", 0.8)]


def test_best_match_pairs_below_threshold_excluded():
    sims = {("a.py", "b.py"): 0.1}
    assert _best_match_pairs(sims, threshold=0.25) == []


def test_best_match_pairs_each_file_used_once():
    """Greedy: each file appears in at most one pair."""
    sims = {
        ("a.py", "x.py"): 0.9,
        ("a.py", "y.py"): 0.8,  # a.py already used → skipped
        ("b.py", "x.py"): 0.7,  # x.py already used → skipped
        ("b.py", "y.py"): 0.6,
    }
    result = _best_match_pairs(sims, threshold=0.25)
    assert len(result) == 2
    assert result[0] == ("a.py", "x.py", 0.9)
    assert result[1] == ("b.py", "y.py", 0.6)


def test_best_match_pairs_sorted_by_sim_desc():
    sims = {("a.py", "x.py"): 0.5, ("b.py", "y.py"): 0.9}
    result = _best_match_pairs(sims, threshold=0.25)
    assert result[0][2] >= result[1][2]


# --- Cross-file cosine: renamed copy detection ---

_LONG_DIFF = (
    "+def bubble_sort(arr):\n"
    "+    n = len(arr)\n"
    "+    for i in range(n):\n"
    "+        for j in range(0, n - i - 1):\n"
    "+            if arr[j] > arr[j + 1]:\n"
    "+                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n"
    "+    return arr\n"
) * 3  # repeat to exceed 10-word threshold


def test_cosine_cross_file_detects_renamed_copy():
    """Same content, different filenames within same exercise → renamed match found."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1",
                        file_name="bubble_sort.py", diff_content=_LONG_DIFF)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1",
                        file_name="my_sort.py", diff_content=_LONG_DIFF)],
    }
    result = _compute_cosine_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert score > 0.5
    assert len(matches) == 1
    m = matches[0]
    assert m["renamed"] is True
    assert m["file_name"] == "bubble_sort.py"
    assert m["file_name_b"] == "my_sort.py"


def test_cosine_same_name_match_has_renamed_false():
    """Same filename match has renamed=False and file_name_b == file_name."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1",
                        file_name="sol.py", diff_content=_LONG_DIFF)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1",
                        file_name="sol.py", diff_content=_LONG_DIFF)],
    }
    result = _compute_cosine_scores([1, 2], commits)
    _, matches = result[(1, 2)]
    assert len(matches) == 1
    assert matches[0]["renamed"] is False
    assert matches[0]["file_name_b"] == "sol.py"


def test_cosine_cross_file_different_exercises_no_match():
    """Files in different exercises are never cross-matched."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1",
                        file_name="a.py", diff_content=_LONG_DIFF)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex2",
                        file_name="b.py", diff_content=_LONG_DIFF)],
    }
    result = _compute_cosine_scores([1, 2], commits)
    score, matches = result[(1, 2)]
    assert score == 0.0
    assert matches == []


# --- Cross-file structural: renamed copy detection ---

_STRUCT_DIFF = (
    "+def bubble_sort(arr, length):\n"
    "+    for outer in range(length):\n"
    "+        for inner in range(0, length - outer - 1):\n"
    "+            if arr[inner] > arr[inner + 1]:\n"
    "+                arr[inner], arr[inner + 1] = arr[inner + 1], arr[inner]\n"
    "+    return arr\n"
)


def test_structural_cross_file_detects_renamed_copy():
    """Same structure, different filenames within same exercise → renamed match found."""
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1",
                        file_name="bubble_sort.py", diff_content=_STRUCT_DIFF)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1",
                        file_name="my_sort.py", diff_content=_STRUCT_DIFF)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=3)
    score, matches = result[(1, 2)]
    assert score > 0.5
    assert len(matches) == 1
    m = matches[0]
    assert m["renamed"] is True
    assert m["file_name"] == "bubble_sort.py"
    assert m["file_name_b"] == "my_sort.py"
    assert "shared_tokens" in m


def test_structural_same_name_match_has_renamed_false():
    """Same filename structural match has renamed=False."""
    diff = "+def compute(value, factor):\n+    total = value * factor\n+    return total\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1",
                        file_name="sol.py", diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1",
                        file_name="sol.py", diff_content=diff)],
    }
    result = _compute_structural_scores([1, 2], commits, min_tokens=2)
    _, matches = result[(1, 2)]
    assert len(matches) == 1
    assert matches[0]["renamed"] is False
    assert matches[0]["file_name_b"] == "sol.py"


# --- End-to-end analyze_group ---

def test_analyze_group_less_than_two_students():
    result = analyze_group({1: [make_commit(1, "2026-06-01T08:05:00Z")]})
    assert result.nodes == [1]
    assert result.edges == []


def test_analyze_group_all_identical_commits():
    diff = "+def solve(items):\n+    result = sum(items)\n+    count = len(items)\n+    return result / count\n"
    same_commits = lambda sid: [
        make_commit(sid, "2026-06-01T08:05:00Z", exercise_id="ex1",
                    file_name="sol.py", lines_added=100, diff_content=diff)
    ]
    commits = {1: same_commits(1), 2: same_commits(2)}
    result = analyze_group(commits, edge_threshold=0.5)
    assert len(result.nodes) == 2
    assert any(e.score >= 0.5 for e in result.edges)


def test_analyze_group_edge_threshold_zero_returns_all():
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z")],
        2: [make_commit(2, "2026-06-01T09:00:00Z", exercise_id="ex99", file_name="z.py")],
    }
    result = analyze_group(commits, edge_threshold=0.0)
    assert len(result.edges) == 1  # one pair exists


def test_analyze_group_edge_details_include_match_lists():
    """edges include cosine_matches and structural_matches keys."""
    diff = "+def solve(items):\n+    result = sum(items)\n+    count = len(items)\n+    return result / count\n"
    commits = {
        1: [make_commit(1, "2026-06-01T08:05:00Z", exercise_id="ex1", file_name="sol.py",
                        diff_content=diff)],
        2: [make_commit(2, "2026-06-01T08:06:00Z", exercise_id="ex1", file_name="sol.py",
                        diff_content=diff)],
    }
    result = analyze_group(commits, edge_threshold=0.0)
    assert len(result.edges) == 1
    details = result.edges[0].details
    assert "cosine_matches" in details
    assert "structural_matches" in details
    assert isinstance(details["cosine_matches"], list)
    assert isinstance(details["structural_matches"], list)


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
