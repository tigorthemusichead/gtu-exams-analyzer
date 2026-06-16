"""Group similarity analysis service.

Pure Python computation module — no FastAPI, no DB queries.
Detects potential copying between students by comparing commit patterns
across three dimensions: cosine similarity (TF-IDF), structural similarity
(AST-based naming patterns), and sequential commit correlation (timing).
"""

import ast
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.analysis_individual import CommitRecord

CROSS_FILE_MIN_SIM_COSINE = 0.25
CROSS_FILE_MIN_SIM_STRUCTURAL = 0.20


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


def _get_ts_language(ext: str):
    """Return a tree-sitter Language for the given file extension, or None.

    Returns None if tree-sitter or the grammar package is not installed,
    or if the extension is not recognised.
    """
    try:
        from tree_sitter import Language
        if ext in (".c", ".h"):
            import tree_sitter_c as m
            return Language(m.language())
        if ext in (".cpp", ".cc", ".cxx", ".hpp"):
            import tree_sitter_cpp as m
            return Language(m.language())
        if ext == ".cs":
            import tree_sitter_c_sharp as m
            return Language(m.language())
        if ext == ".java":
            import tree_sitter_java as m
            return Language(m.language())
        if ext in (".js", ".mjs"):
            import tree_sitter_javascript as m
            return Language(m.language())
        if ext == ".ts":
            import tree_sitter_typescript as m
            return Language(m.language_typescript())
    except Exception:
        return None
    return None


def _walk_ts_node(root_node) -> set[str]:
    """Iteratively walk a tree-sitter node tree and collect identifier strings."""
    _IDENT_TYPES = frozenset({
        "identifier",
        "type_identifier",
        "field_identifier",
        "property_identifier",
    })
    tokens: set[str] = set()
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type in _IDENT_TYPES:
            text = node.text.decode("utf-8", errors="replace")
            if len(text) > 1:
                tokens.add(text)
        stack.extend(node.children)
    return tokens


def _extract_ast_tokens_treesitter(source: str, ext: str) -> set[str]:
    """Extract identifier tokens using tree-sitter for non-Python languages.

    Falls back to empty set if the grammar is unavailable or parsing fails.
    """
    lang = _get_ts_language(ext)
    if lang is None:
        return set()
    try:
        from tree_sitter import Parser
        parser = Parser(lang)
        tree = parser.parse(source.encode("utf-8", errors="replace"))
        return _walk_ts_node(tree.root_node)
    except Exception:
        return set()


def _extract_ast_tokens(diff_content: str, file_name: str = "") -> set[str]:
    """Extract identifier names from code in a diff.

    Dispatches by file extension:
    - .py (or no extension): built-in ast module, extracts function/class/variable names.
    - .c .h .cpp .cc .cxx .hpp .cs .java .js .mjs .ts: tree-sitter grammars,
      extracts identifier, type_identifier, field_identifier, property_identifier nodes.

    Parses only added lines (starting with '+') from the diff.
    Falls back to empty set on any parse error.
    """
    added_lines = []
    for line in diff_content.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])  # strip leading '+'

    source = "\n".join(added_lines)
    ext = os.path.splitext(file_name)[1].lower() if file_name else ""

    if ext not in (".c", ".h", ".cpp", ".cc", ".cxx", ".hpp",
                   ".cs", ".java", ".js", ".mjs", ".ts"):
        # Python path (also used as fallback for unknown extensions)
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
        # strip single-char names and Python keywords that add noise
        return {t for t in tokens if len(t) > 1}

    return _extract_ast_tokens_treesitter(source, ext)


def _group_commits_by_file(
    commits: list[CommitRecord],
) -> dict[tuple[str, str], list[CommitRecord]]:
    """Group commits by (exercise_id, file_name). Shared by cosine and structural."""
    groups: dict[tuple[str, str], list[CommitRecord]] = {}
    for c in commits:
        groups.setdefault((c.exercise_id, c.file_name), []).append(c)
    return groups


def _build_file_doc(commits: list[CommitRecord]) -> str:
    """Concatenate added lines from all commits in a file bucket."""
    parts = []
    for c in commits:
        if c.diff_content:
            for line in c.diff_content.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    parts.append(line[1:])
    return "\n".join(parts)


def _best_match_pairs(
    sims: dict[tuple[str, str], float],
    threshold: float = 0.25,
) -> list[tuple[str, str, float]]:
    """Greedy best-match pairing from a similarity matrix.

    sims: {(file_a, file_b): similarity}
    Returns sorted list of (file_a, file_b, sim) where each file appears at
    most once and sim >= threshold.
    """
    ranked = sorted(sims.items(), key=lambda x: x[1], reverse=True)
    used_a: set[str] = set()
    used_b: set[str] = set()
    result = []
    for (fa, fb), sim in ranked:
        if sim < threshold:
            break
        if fa not in used_a and fb not in used_b:
            result.append((fa, fb, sim))
            used_a.add(fa)
            used_b.add(fb)
    return result


def _cosine_two_docs(
    commits_a: list[CommitRecord],
    commits_b: list[CommitRecord],
) -> tuple[float, str, str]:
    """Build docs from two commit lists and compute cosine (word-overlap fallback for short docs).

    Returns (similarity, doc_a, doc_b). Returns (0.0, doc_a, doc_b) when either doc is empty.
    """
    doc_a = _build_file_doc(commits_a)
    doc_b = _build_file_doc(commits_b)

    if not doc_a.strip() or not doc_b.strip():
        return 0.0, doc_a, doc_b

    words_a = doc_a.split()
    words_b = doc_b.split()

    if len(words_a) < 10 or len(words_b) < 10:
        set_a = set(words_a)
        set_b = set(words_b)
        union = set_a | set_b
        sim = len(set_a & set_b) / len(union) if union else 0.0
    else:
        try:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([doc_a, doc_b])
            sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        except Exception:
            return 0.0, doc_a, doc_b

    return sim, doc_a, doc_b


def _compute_cosine_scores(
    student_ids: list[int],
    commits_by_student: dict[int, list[CommitRecord]],
) -> dict[tuple[int, int], tuple[float, list[dict]]]:
    """Compute pairwise cosine similarity using TF-IDF on commit content, per file.

    For each (exercise_id, file_name) bucket shared by both students, builds a
    per-file TF-IDF document from added diff lines and computes cosine similarity.
    Falls back to raw token overlap ratio when either document has fewer than 10 words.

    Returns a dict mapping (student_a_id, student_b_id) ->
        (aggregate_score, list_of_match_dicts sorted by similarity desc)
    where student_a_id < student_b_id.
    """
    if len(student_ids) < 2:
        return {}

    # Group by student → exercise_id → file_name → commits
    by_exercise: dict[int, dict[str, dict[str, list[CommitRecord]]]] = {}
    for sid in student_ids:
        by_exercise[sid] = {}
        for (ex_id, fname), commits in _group_commits_by_file(commits_by_student[sid]).items():
            by_exercise[sid].setdefault(ex_id, {})[fname] = commits

    result: dict[tuple[int, int], tuple[float, list[dict]]] = {}

    for i, j in combinations(range(len(student_ids)), 2):
        a = student_ids[i]
        b = student_ids[j]
        if a > b:
            a, b = b, a

        files_by_ex_a = by_exercise[a]
        files_by_ex_b = by_exercise[b]
        all_exercises = set(files_by_ex_a) | set(files_by_ex_b)

        matches: list[dict] = []
        sim_values: list[float] = []

        for ex_id in all_exercises:
            files_a = files_by_ex_a.get(ex_id, {})
            files_b = files_by_ex_b.get(ex_id, {})

            matched_a: set[str] = set()
            matched_b: set[str] = set()

            # Same-filename pairs (fast path, highest confidence)
            for fname in set(files_a) & set(files_b):
                sim, doc_a, doc_b = _cosine_two_docs(files_a[fname], files_b[fname])
                if not doc_a.strip() or not doc_b.strip():
                    continue
                matches.append({
                    "exercise_id": ex_id,
                    "file_name": fname,
                    "file_name_b": fname,
                    "renamed": False,
                    "similarity": sim,
                    "snippet_a": doc_a[:800],
                    "snippet_b": doc_b[:800],
                })
                sim_values.append(sim)
                matched_a.add(fname)
                matched_b.add(fname)

            # Cross-file best-match for unmatched files within the same exercise
            unmatched_a = {f: files_a[f] for f in files_a if f not in matched_a}
            unmatched_b = {f: files_b[f] for f in files_b if f not in matched_b}

            if unmatched_a and unmatched_b:
                cross_sims: dict[tuple[str, str], float] = {}
                cross_docs: dict[tuple[str, str], tuple[str, str]] = {}
                for fa, commits_a_list in unmatched_a.items():
                    for fb, commits_b_list in unmatched_b.items():
                        sim, da, db = _cosine_two_docs(commits_a_list, commits_b_list)
                        if da.strip() and db.strip():
                            cross_sims[(fa, fb)] = sim
                            cross_docs[(fa, fb)] = (da, db)

                for fa, fb, sim in _best_match_pairs(cross_sims, threshold=CROSS_FILE_MIN_SIM_COSINE):
                    da, db = cross_docs[(fa, fb)]
                    matches.append({
                        "exercise_id": ex_id,
                        "file_name": fa,
                        "file_name_b": fb,
                        "renamed": True,
                        "similarity": sim,
                        "snippet_a": da[:800],
                        "snippet_b": db[:800],
                    })
                    sim_values.append(sim)

        aggregate = sum(sim_values) / len(sim_values) if sim_values else 0.0
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        result[(a, b)] = (aggregate, matches)

    return result


def _extract_file_tokens(commits: list[CommitRecord]) -> set[str]:
    """Union of AST identifier tokens across all commits in a file bucket."""
    tokens: set[str] = set()
    for c in commits:
        if c.diff_content:
            tokens |= _extract_ast_tokens(c.diff_content, c.file_name)
    return tokens


def _compute_structural_scores(
    student_ids: list[int],
    commits_by_student: dict[int, list[CommitRecord]],
    min_tokens: int = 3,
) -> dict[tuple[int, int], tuple[float, list[dict]]]:
    """Compute pairwise Jaccard similarity on AST identifier tokens, per file.

    For each (exercise_id, file_name) bucket shared by both students, extracts
    AST identifier tokens from diff content and computes Jaccard similarity.
    Buckets with fewer than min_tokens identifiers on either side are skipped.
    Aggregate score is weighted by union token set size.

    Returns a dict mapping (student_a_id, student_b_id) ->
        (aggregate_score, list_of_match_dicts sorted by similarity desc)
    where student_a_id < student_b_id.
    """
    # Group by student → exercise_id → file_name → commits
    by_exercise: dict[int, dict[str, dict[str, list[CommitRecord]]]] = {}
    for sid in student_ids:
        by_exercise[sid] = {}
        for (ex_id, fname), commits in _group_commits_by_file(commits_by_student[sid]).items():
            by_exercise[sid].setdefault(ex_id, {})[fname] = commits

    result: dict[tuple[int, int], tuple[float, list[dict]]] = {}

    for i, j in combinations(range(len(student_ids)), 2):
        a = student_ids[i]
        b = student_ids[j]
        if a > b:
            a, b = b, a

        files_by_ex_a = by_exercise[a]
        files_by_ex_b = by_exercise[b]
        all_exercises = set(files_by_ex_a) | set(files_by_ex_b)

        matches: list[dict] = []
        weighted: list[tuple[float, int]] = []  # (similarity, weight=|union|)

        for ex_id in all_exercises:
            files_a = files_by_ex_a.get(ex_id, {})
            files_b = files_by_ex_b.get(ex_id, {})

            matched_a: set[str] = set()
            matched_b: set[str] = set()

            # Same-filename pairs (fast path, highest confidence)
            for fname in set(files_a) & set(files_b):
                tokens_a = _extract_file_tokens(files_a[fname])
                tokens_b = _extract_file_tokens(files_b[fname])
                if len(tokens_a) < min_tokens or len(tokens_b) < min_tokens:
                    continue
                union = tokens_a | tokens_b
                if not union:
                    continue
                sim = len(tokens_a & tokens_b) / len(union)
                matches.append({
                    "exercise_id": ex_id,
                    "file_name": fname,
                    "file_name_b": fname,
                    "renamed": False,
                    "similarity": sim,
                    "shared_tokens": sorted(tokens_a & tokens_b),
                    "tokens_a": sorted(tokens_a),
                    "tokens_b": sorted(tokens_b),
                })
                weighted.append((sim, len(union)))
                matched_a.add(fname)
                matched_b.add(fname)

            # Cross-file best-match for unmatched files within the same exercise
            unmatched_a = {f: files_a[f] for f in files_a if f not in matched_a}
            unmatched_b = {f: files_b[f] for f in files_b if f not in matched_b}

            if unmatched_a and unmatched_b:
                cross_sims: dict[tuple[str, str], float] = {}
                cross_tokens: dict[tuple[str, str], tuple[set, set]] = {}
                for fa, commits_a_list in unmatched_a.items():
                    ta = _extract_file_tokens(commits_a_list)
                    if len(ta) < min_tokens:
                        continue
                    for fb, commits_b_list in unmatched_b.items():
                        tb = _extract_file_tokens(commits_b_list)
                        if len(tb) < min_tokens:
                            continue
                        union_cross = ta | tb
                        if not union_cross:
                            continue
                        cross_sims[(fa, fb)] = len(ta & tb) / len(union_cross)
                        cross_tokens[(fa, fb)] = (ta, tb)

                for fa, fb, sim in _best_match_pairs(cross_sims, threshold=CROSS_FILE_MIN_SIM_STRUCTURAL):
                    ta, tb = cross_tokens[(fa, fb)]
                    union_pair = ta | tb
                    matches.append({
                        "exercise_id": ex_id,
                        "file_name": fa,
                        "file_name_b": fb,
                        "renamed": True,
                        "similarity": sim,
                        "shared_tokens": sorted(ta & tb),
                        "tokens_a": sorted(ta),
                        "tokens_b": sorted(tb),
                    })
                    weighted.append((sim, len(union_pair)))

        if weighted:
            total_weight = sum(w for _, w in weighted)
            aggregate = (
                sum(s * w for s, w in weighted) / total_weight
                if total_weight > 0
                else sum(s for s, _ in weighted) / len(weighted)
            )
        else:
            aggregate = 0.0

        matches.sort(key=lambda x: x["similarity"], reverse=True)
        result[(a, b)] = (aggregate, matches)

    return result


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
    tokens_a = _extract_ast_tokens(ca.diff_content, ca.file_name)
    tokens_b = _extract_ast_tokens(cb.diff_content, cb.file_name)
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
        (score, matched_pairs) where matched_pairs is a list of all dicts
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
                        tokens_a = _extract_ast_tokens(ca.diff_content, ca.file_name)
                        tokens_b = _extract_ast_tokens(cb.diff_content, cb.file_name)
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

    cosine_result = _compute_cosine_scores(student_ids, commits_by_student)
    structural_result = _compute_structural_scores(
        student_ids, commits_by_student, min_tokens=sequential_min_tokens
    )
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
        cosine, cosine_matches = cosine_result.get(key, (0.0, []))
        structural, structural_matches = structural_result.get(key, (0.0, []))
        seq_score, seq_matches = seq_result.get(key, (0.0, []))

        combined = (
            weight_cosine * cosine
            + weight_structural * structural
            + weight_sequential * seq_score
        )

        # combined = 1 - (1 - cosine) * (1 - structural) * (1 - seq_score)

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
                    "cosine_matches": cosine_matches,
                    "structural_matches": structural_matches,
                },
            ))

    return GroupAnalysisResult(nodes=student_ids, edges=edges)
