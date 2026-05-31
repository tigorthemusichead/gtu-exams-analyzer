# TASK-029: Fix diff_content always NULL in commits table

status: done
created: 2026-05-31
updated: 2026-05-31

## Description

`diff_content` column is always NULL in the `commits` table because the client
never sends the diff in the POST /commits payload.

**Root cause:** `git_watcher.py:107–110` computes `diff_text` inside
`if diff.diff:` block, but the `payloads.append(...)` call at lines 119–128
omits the `"diff"` key entirely. Server receives no `diff` field →
`CommitIngestionItem.diff` defaults to `None` → `diff_content` stored as NULL.

**Fix plan:**

1. In `client/app/git_watcher.py`, initialize `diff_text = None` before the
   `if diff.diff:` block (line 106) so the variable is always defined.
2. Add `"diff": diff_text` to the `payloads.append(...)` dict (after
   `"lines_removed"`).

```python
# Before (lines 104–128):
lines_added = 0
lines_removed = 0
if diff.diff:
    diff_text = (
        diff.diff.decode("utf-8", errors="replace")
        if isinstance(diff.diff, bytes)
        else diff.diff
    )
    for line in diff_text.splitlines():
        ...

file_name = diff.b_path or diff.a_path or "unknown"
payloads.append({
    "commit_id": commit.hexsha,
    ...
    "lines_removed": lines_removed,
    # ← "diff" key missing!
})

# After:
lines_added = 0
lines_removed = 0
diff_text = None          # ← initialize
if diff.diff:
    diff_text = (
        diff.diff.decode("utf-8", errors="replace")
        if isinstance(diff.diff, bytes)
        else diff.diff
    )
    for line in diff_text.splitlines():
        ...

file_name = diff.b_path or diff.a_path or "unknown"
payloads.append({
    "commit_id": commit.hexsha,
    ...
    "lines_removed": lines_removed,
    "diff": diff_text,    # ← add this
})
```

No server-side changes needed. `CommitIngestionItem.diff` is already
`str | None` and `commits.py` already maps it to `diff_content`.

## Acceptance criteria

- [ ] `diff_text = None` initialized before `if diff.diff:` block
- [ ] `"diff": diff_text` present in `payloads.append(...)` dict
- [ ] New commits in DB have non-NULL `diff_content` for files with changes
- [ ] Empty/binary diffs still store NULL (not crash)
- [ ] Existing client unit tests pass

## Notes

Affects structural similarity scoring in group analysis — `diff_content` NULL
causes `_extract_ast_tokens` to be skipped, making structural similarity always
0 and reducing cheat detection accuracy.
