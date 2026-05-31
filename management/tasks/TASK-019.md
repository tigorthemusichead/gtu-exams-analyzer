# TASK-019: AST-based structural code analysis

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
The project spec requires: "структурная близость за счет классификации по именам функций, переменных, стилю комментариев" (structural similarity based on function names, variable names, comment style).

Current `analysis_group.py` `_compute_structural_scores()` does Jaccard on file/exercise names only — this is NOT what the spec describes.

Replace or augment with true code-level structural analysis:
- Parse Python code from commit diffs using `ast` module
- Extract: function names, class names, variable names (assignments), parameter names
- Build token sets per student from extracted names
- Compute Jaccard similarity on these sets (not just filenames)
- Also extract comment text and include in TF-IDF corpus for cosine score

Server receives `lines_added`/`lines_removed` counts but not raw diff content currently. Need to assess whether:
a) Server should store raw diff text (requires schema + API change), or
b) Client sends additional `diff_content` field

Decide approach, update schema if needed, implement AST extraction in analysis service.

## Acceptance criteria
- [ ] Structural score uses extracted function/variable/class names, not just file names
- [ ] AST parsing handles syntax errors gracefully (fallback to filename Jaccard)
- [ ] If schema extended: migration created, API updated, client sends diff_content
- [ ] Unit tests cover AST extraction with sample Python code snippets

## Notes
Python `ast` module is stdlib. For non-Python files, fallback to filename/token Jaccard.
This is the most technically complex remaining task.
