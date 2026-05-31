"""Group similarity analysis service.

Pure Python computation module — no FastAPI, no DB queries.
Detects potential copying between students by comparing commit patterns
across three dimensions: cosine similarity (TF-IDF), structural similarity
(AST-based naming patterns), and sequential commit correlation (timing).
"""

import ast
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.analysis_individual import CommitRecord


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO 8601 string to an aware datetime (UTC)."""
    ts = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class SimilarityEdge:
    student_a: int
    student_b: int
    score: float      # combined 0-1
    details: dict     # {"cosine": float, "structural": float, "sequential": float}


@dataclass
class GroupAnalysisResult:
    nodes: list[int]           # list of student_ids
    edges: list[SimilarityEdge]  # only edges above threshold


def _extract_ast_tokens(diff_content: str) -> set[str]:
    """Extract identifier names from Python code in a diff.

    Parses added lines (lines starting with '+') from the diff as Python source.
    Extracts: function names, class names, variable names, parameter names.
    Falls back to empty set on any parse error.
    """
    added_lines = []
    for line in diff_content.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])  # strip leading '+'

    source = "\n".join(added_lines)
    tokens: set[str] = set()
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                tokens.add(node.name)
                for arg in node.args.args:
                    tokens.add(arg.arg)
            elif isinstance(node, ast.ClassDef):
                tokens.add(node.name)
            elif isinstance(node, ast.Name):
                tokens.add(node.id)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        tokens.add(target.id)
    except SyntaxError:
        pass
    # strip built-in single-char names and Python keywords that add noise
    return {t for t in tokens if len(t) > 1}


def _build_corpus_doc(commits: list[CommitRecord]) -> str:
    """Build a single text document representing a student's commit activity."""
    parts = []
    for c in commits:
        token = (
            f"{c.exercise_id} {c.file_name} "
            + " ".join(["add"] * c.lines_added + ["remove"] * c.lines_removed)
        )
        parts.append(token)
    return " ".join(parts)


def _compute_cosine_scores(
    student_ids: list[int],
    commits_by_student: dict[int, list[CommitRecord]],
) -> dict[tuple[int, int], float]:
    """Compute pairwise cosine similarity using TF-IDF on commit content.

    Returns a dict mapping (student_a_id, student_b_id) -> float in [0, 1]
    where student_a_id < student_b_id.
    """
    if len(student_ids) < 2:
        return {}

    corpus = [_build_corpus_doc(commits_by_student[sid]) for sid in student_ids]

    # Handle edge case: all documents are empty strings
    if all(doc.strip() == "" for doc in corpus):
        return {
            (a, b): 0.0
            for a, b in combinations(student_ids, 2)
        }

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    sim_matrix = cosine_similarity(tfidf_matrix)

    scores: dict[tuple[int, int], float] = {}
    for i, j in combinations(range(len(student_ids)), 2):
        a = student_ids[i]
        b = student_ids[j]
        if a > b:
            a, b = b, a
        scores[(a, b)] = float(sim_matrix[i, j])

    return scores


def _build_structural_token_set(commits: list[CommitRecord]) -> set[str]:
    """Build a token set for structural similarity.

    Uses AST-extracted identifiers from diff_content when available (Python files).
    Falls back to exercise_id + file_name tokens for non-Python files or missing diffs.
    """
    tokens: set[str] = set()
    for c in commits:
        # Always include exercise/file tokens as baseline
        tokens.add(c.exercise_id)
        tokens.add(c.file_name)

        if c.diff_content and c.file_name.endswith(".py"):
            ast_tokens = _extract_ast_tokens(c.diff_content)
            tokens |= ast_tokens

    return tokens


def _compute_structural_scores(
    student_ids: list[int],
    commits_by_student: dict[int, list[CommitRecord]],
) -> dict[tuple[int, int], float]:
    """Compute pairwise Jaccard similarity on structural code tokens.

    For Python files with diff content, uses AST-extracted identifiers
    (function names, class names, variable names, parameter names).
    Falls back to exercise_id + file_name tokens otherwise.

    Returns a dict mapping (student_a_id, student_b_id) -> float in [0, 1]
    where student_a_id < student_b_id.
    """
    token_sets: dict[int, set[str]] = {
        sid: _build_structural_token_set(commits_by_student[sid])
        for sid in student_ids
    }

    scores: dict[tuple[int, int], float] = {}
    for i, j in combinations(range(len(student_ids)), 2):
        a = student_ids[i]
        b = student_ids[j]
        if a > b:
            a, b = b, a
        set_a = token_sets[a]
        set_b = token_sets[b]
        union = set_a | set_b
        if not union:
            scores[(a, b)] = 0.0
        else:
            scores[(a, b)] = len(set_a & set_b) / len(union)

    return scores


def _commits_content_similar(
    ca: "CommitRecord",
    cb: "CommitRecord",
    threshold: float,
    min_tokens: int,
) -> bool:
    """Return True if ca and cb share enough AST tokens (Jaccard >= threshold).

    Returns False if either diff is None or either token set is too small.
    """
    if ca.diff_content is None or cb.diff_content is None:
        return False
    tokens_a = _extract_ast_tokens(ca.diff_content)
    tokens_b = _extract_ast_tokens(cb.diff_content)
    if len(tokens_a) < min_tokens or len(tokens_b) < min_tokens:
        return False
    union = tokens_a | tokens_b
    if not union:
        return False
    return len(tokens_a & tokens_b) / len(union) >= threshold


def _compute_sequential_scores(
    student_ids: list[int],
    commits_by_student: dict[int, list[CommitRecord]],
    sequential_window_seconds: int,
    content_threshold: float,
    min_tokens: int,
) -> dict[tuple[int, int], tuple[float, list[dict]]]:
    """Compute pairwise sequential commit correlation requiring timing AND content match.

    A commit pair (ca, cb) is counted as correlated only when:
      1. |ca.timestamp - cb.timestamp| <= sequential_window_seconds
      2. Jaccard similarity of AST token sets >= content_threshold
         (with each token set having at least min_tokens elements)

    The score is correlated_pairs / max(len(commits_A), len(commits_B)), capped at 1.0.

    Returns a dict mapping (student_a_id, student_b_id) ->
        (score, matched_pairs) where matched_pairs is a list of up to 5 dicts
        sorted by similarity descending.
    """
    scores: dict[tuple[int, int], tuple[float, list[dict]]] = {}
    for i, j in combinations(range(len(student_ids)), 2):
        a = student_ids[i]
        b = student_ids[j]
        if a > b:
            a, b = b, a

        commits_a = commits_by_student[a]
        commits_b = commits_by_student[b]

        if not commits_a or not commits_b:
            scores[(a, b)] = (0.0, [])
            continue

        correlated = 0
        matched_pairs: list[dict] = []

        for ca in commits_a:
            ta = _parse_iso(ca.timestamp)
            for cb in commits_b:
                tb = _parse_iso(cb.timestamp)
                if abs((ta - tb).total_seconds()) <= sequential_window_seconds:
                    if _commits_content_similar(ca, cb, content_threshold, min_tokens):
                        correlated += 1
                        tokens_a = _extract_ast_tokens(ca.diff_content)
                        tokens_b = _extract_ast_tokens(cb.diff_content)
                        union = tokens_a | tokens_b
                        sim = len(tokens_a & tokens_b) / len(union) if union else 0.0
                        matched_pairs.append({
                            "commit_a": ca.commit_id,
                            "commit_b": cb.commit_id,
                            "similarity": sim,
                            "timestamp_a": ca.timestamp,
                            "timestamp_b": cb.timestamp,
                            "diff_a": ca.diff_content[:800],
                            "diff_b": cb.diff_content[:800],
                            "exercise_id": ca.exercise_id,
                            "file_name": ca.file_name,
                            "who_first": "a" if ta <= tb else "b",
                        })
                        break  # count each commit in A at most once

        matched_pairs.sort(key=lambda x: x["similarity"], reverse=True)
        matched_pairs = matched_pairs[:5]

        denominator = max(len(commits_a), len(commits_b))
        scores[(a, b)] = (min(1.0, correlated / denominator), matched_pairs)

    return scores


def analyze_group(
    commits_by_student: dict[int, list[CommitRecord]],
    weight_cosine: float = 0.5,
    weight_structural: float = 0.3,
    weight_sequential: float = 0.2,
    edge_threshold: float = 0.6,
    sequential_window_seconds: int = 300,
    sequential_content_threshold: float = 0.4,
    sequential_min_tokens: int = 3,
) -> GroupAnalysisResult:
    """Analyse a group of students for potential copying.

    Parameters
    ----------
    commits_by_student:
        Mapping from student_id to that student's list of CommitRecord objects.
    weight_cosine:
        Weight for the TF-IDF cosine similarity component (default 0.5).
    weight_structural:
        Weight for the structural (Jaccard) similarity component (default 0.3).
    weight_sequential:
        Weight for the sequential correlation component (default 0.2).
    edge_threshold:
        Minimum combined score for a pair to be included as an edge (default 0.6).
    sequential_window_seconds:
        Maximum seconds between two commits to consider them temporally
        correlated (default 300).
    sequential_content_threshold:
        Minimum Jaccard similarity of AST token sets for a commit pair to count
        as correlated (default 0.4).
    sequential_min_tokens:
        Minimum token set size required on each commit before comparison;
        pairs with fewer tokens are skipped (default 3).

    Returns
    -------
    GroupAnalysisResult with all student IDs as nodes and suspicious pairs
    as edges.
    """
    student_ids = list(commits_by_student.keys())

    if len(student_ids) < 2:
        return GroupAnalysisResult(nodes=student_ids, edges=[])

    cosine_scores = _compute_cosine_scores(student_ids, commits_by_student)
    structural_scores = _compute_structural_scores(student_ids, commits_by_student)
    seq_result = _compute_sequential_scores(
        student_ids,
        commits_by_student,
        sequential_window_seconds,
        sequential_content_threshold,
        sequential_min_tokens,
    )

    edges: list[SimilarityEdge] = []
    for a, b in combinations(sorted(student_ids), 2):
        key = (a, b) if a < b else (b, a)
        cosine = cosine_scores.get(key, 0.0)
        structural = structural_scores.get(key, 0.0)
        seq_score, seq_matches = seq_result.get(key, (0.0, []))

        combined = (
            weight_cosine * cosine
            + weight_structural * structural
            + weight_sequential * seq_score
        )

        if combined >= edge_threshold:
            edges.append(SimilarityEdge(
                student_a=min(a, b),
                student_b=max(a, b),
                score=combined,
                details={
                    "cosine": cosine,
                    "structural": structural,
                    "sequential": seq_score,
                    "sequential_matches": seq_matches,
                },
            ))

    return GroupAnalysisResult(nodes=student_ids, edges=edges)
