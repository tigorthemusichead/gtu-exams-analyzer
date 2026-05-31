# TASK-030: Sequential commit match evidence in pair similarity modal

status: done
created: 2026-05-31
updated: 2026-05-31 (implemented)

## Description

Upgrade sequential similarity analysis to require both timing AND content similarity
between commits, and display the matched commit pairs as evidence in the suspect pair
detail modal.

Currently `_compute_sequential_scores()` only checks timing — a commit from student A
is counted as correlated if any commit from student B happened within 300 seconds,
regardless of content. This produces false positives when two students independently
solve the same exercise at overlapping times.

The new behavior: a commit pair (ca, cb) is only counted as correlated if BOTH:
1. `|ca.timestamp - cb.timestamp| <= sequential_window_seconds` (currently 300s)
2. Jaccard similarity of AST token sets from their diffs >= `SEQUENTIAL_CONTENT_THRESHOLD`

Matched pairs are stored in `SimilarityPair.details` JSON and rendered in the modal.

## Implementation plan

### Step 1 — `server/app/config.py`
Add two new settings:
- `SEQUENTIAL_CONTENT_THRESHOLD: float = 0.4` — minimum Jaccard similarity to count a commit pair as correlated
- `SEQUENTIAL_MIN_TOKEN_COUNT: int = 3` — minimum AST token set size required on each commit before comparison (avoids noise from trivial one-liner commits like `return result`)

### Step 2 — `server/app/services/analysis_group.py`

Add helper function `_commits_content_similar(ca, cb, threshold, min_tokens) -> bool`:
- Extract AST tokens from `ca.diff_content` and `cb.diff_content` using existing `_extract_ast_tokens()`
- If either diff is None or either token set is smaller than `min_tokens`, return False
- Compute Jaccard: `len(A & B) / len(A | B)`
- Return `jaccard >= threshold`

Change `_compute_sequential_scores()`:
- Accept full `commits_by_student: dict[int, list[CommitRecord]]` instead of just timestamps (already available in `analyze_group()` call site, just not passed through)
- Add `content_threshold: float` and `min_tokens: int` parameters
- In the inner loop, add content similarity check after timing check
- Collect matched pairs: for each correlated (ca, cb) pair store `{commit_a, commit_b, similarity, timestamp_a, timestamp_b, diff_a, diff_b}` — truncate diffs to 800 chars each
- Cap stored matches at top 5 by similarity score
- Return `dict[tuple[int,int], tuple[float, list[dict]]]` — score + matched pairs list

Update `analyze_group()`:
- Pass `content_threshold` and `min_tokens` through to `_compute_sequential_scores()`
- Unpack the new return type

### Step 3 — `server/app/routers/analysis.py`
- Pass `settings.SEQUENTIAL_CONTENT_THRESHOLD` and `settings.SEQUENTIAL_MIN_TOKEN_COUNT` into `analyze_group()`
- Include `sequential_matches` list in `details` JSON when persisting `SimilarityPair`:
```json
{
  "cosine": 0.85,
  "structural": 0.72,
  "sequential": 0.40,
  "sequential_matches": [
    {
      "commit_a": "abc123",
      "commit_b": "def456",
      "similarity": 0.81,
      "timestamp_a": "2024-01-15T10:01:00Z",
      "timestamp_b": "2024-01-15T10:03:30Z",
      "diff_a": "+def solve(x):\n+    return x * 2",
      "diff_b": "+def solve(n):\n+    return n * 2"
    }
  ]
}
```
No DB schema migration needed — `details` column is already a free-form JSON string.

### Step 4 — `server/app/web/templates/report.html`
Add a collapsible section inside the modal `<article>`, below the existing `<dl>`:
```html
<section id="modal-seq-matches" hidden>
  <h5>Sequential commit matches</h5>
  <div id="modal-seq-matches-list"></div>
</section>
```

### Step 5 — `server/app/web/static/js/report.js`
In `showModal(d)`, after populating existing fields:
- If `d.details.sequential_matches` exists and is non-empty, unhide `#modal-seq-matches`
- For each match render a card with:
  - Time delta between the two commits (human-readable, e.g. "2 min 30 sec apart")
  - Similarity score badge
  - Two `<pre>` blocks side-by-side: diff_a (left) and diff_b (right)
- If no matches, keep section hidden

## Acceptance criteria
- [ ] Commit pairs with only timing overlap (no content match) no longer inflate sequential score
- [ ] `SEQUENTIAL_CONTENT_THRESHOLD` and `SEQUENTIAL_MIN_TOKEN_COUNT` configurable in `config.py`
- [ ] `SimilarityPair.details` includes `sequential_matches` array after re-analysis
- [ ] Modal shows matched commit pairs when sequential score > 0
- [ ] Each match card shows time delta, similarity, and both diffs side by side
- [ ] Max 5 matches shown, sorted by similarity descending
- [ ] Missing or empty `sequential_matches` (old analysis data) hides the section gracefully
- [ ] Existing unit tests for `_compute_sequential_scores` updated to reflect new signature
- [ ] New unit test: pair with timing overlap but low content similarity scores 0

## Notes

- `_extract_ast_tokens()` already handles non-Python files (returns empty set) — the `min_tokens` guard naturally skips non-Python diffs without special-casing
- Re-analysis required after deployment to populate `sequential_matches` in existing pairs
- Diff truncation at 800 chars per side keeps `details` JSON size reasonable for large exams
