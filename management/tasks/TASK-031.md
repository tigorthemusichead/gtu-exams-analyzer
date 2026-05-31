# TASK-031: Enhance sequential match display in pair modal (direction + stats)

status: done
created: 2026-05-31
updated: 2026-05-31 (implemented)

## Description

Improve the sequential commit match section inside the edge/pair modal (`#edge-modal`)
by adding directional indicators and an aggregate stats bar. Combines two ideas:
direction badges per match (who committed first) and a score/stats summary header.

## Backend changes — `analysis_group.py`

Extend each dict in `matched_pairs` inside `_compute_sequential_scores` with:

- `exercise_id` — from `ca.exercise_id` (use A's; they should match for a valid pair)
- `file_name` — from `ca.file_name`
- `who_first` — `"a"` if `timestamp_a < timestamp_b`, else `"b"`

No schema or DB changes needed — `details` is stored as JSON blob.

## Frontend changes — `report.js` + `report.html`

### Aggregate stats bar (above match list)
Compute client-side from existing `matched_pairs` array:
- Sequential score progress bar (color-coded by score level)
- Match count: "5 sequential matches"
- Avg time delta between matched pairs
- Direction summary: "B followed A in 4 of 5 matches" (or "mixed direction")

### Per-match card
- Direction badge: `A → B` or `B → A` (derived from new `who_first` field)
- Inline mini-timeline: two labeled dots on shared horizontal axis with delta label
  ```
  [A] ──●──────────────●── [B]
      12:04          12:07  (+3 min)
  ```
- Exercise/file label above diff pair (from new `exercise_id` / `file_name` fields)
- Keep existing: time delta text, token similarity %, side-by-side diffs

## Acceptance criteria

- [ ] `matched_pairs` dicts include `who_first`, `exercise_id`, `file_name`
- [ ] Backend unit tests updated for new fields in sequential match output
- [ ] Stats bar renders above match list with score, count, avg delta, direction summary
- [ ] Each match card shows direction badge (`A → B` / `B → A`)
- [ ] Each match card shows exercise/file label
- [ ] Mini-timeline renders correctly for same-second commits (Δ = 0)
- [ ] Direction summary shows "mixed" when no consistent direction across matches
- [ ] No visual regression on existing cosine/structural score display

## Notes

- `who_first` computed from timestamps already in payload — no extra DB query
- Stats bar uses no new data; pure client-side aggregation of existing `matched_pairs`
- Backend change is small: 3 extra fields in one dict literal (`analysis_group.py:251–259`)
