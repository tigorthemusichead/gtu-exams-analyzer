# TASK-033: Add AST analysis for C++, C, C#, Java, JavaScript

status: done
created: 2026-06-07
updated: 2026-06-16

## Description

Currently structural similarity analysis only extracts AST tokens from Python files (`.py`). The check at `server/app/services/analysis_group.py:139` skips all other languages, falling back to filename + exercise_id tokens only — much weaker signal.

Add language-specific AST token extraction for C++, C, C#, Java, and JavaScript so structural similarity works properly for non-Python courses.

## Acceptance criteria

- [ ] C (`.c`, `.h`) — extract function names, variable declarations, struct/typedef names
- [ ] C++ (`.cpp`, `.cc`, `.cxx`, `.hpp`) — extract function/method names, class names, variable names
- [ ] C# (`.cs`) — extract method names, class names, property names, field names
- [ ] Java (`.java`) — extract method names, class names, field names, parameter names
- [ ] JavaScript (`.js`, `.mjs`, `.ts`) — extract function names, class names, variable/const/let names
- [ ] Each parser must gracefully handle syntax errors (no crash, return empty set or partial tokens)
- [ ] `_extract_ast_tokens()` refactored to dispatch by file extension
- [ ] Existing Python behavior unchanged
- [ ] Unit tests for each new language (at minimum: identical code = high score, unrelated code = low score)

## Notes

Options for multi-language parsing:
- **tree-sitter** (Python binding `tree-sitter` + grammars) — best coverage, single API across all languages
- Per-language tools: `javalang` (Java), `esprima`/`acorn` via subprocess (JS), `libclang` (C/C++)
- tree-sitter recommended — handles malformed code better than most alternatives, single dep

Relevant file: `server/app/services/analysis_group.py`, function `_extract_ast_tokens()` and `_compute_structural_scores()`.
