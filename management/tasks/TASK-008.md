# TASK-008: Group similarity analysis

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Analysis service that detects copying between students by comparing commit content.

Three analysis layers:

1. **Sequential commit correlation**: find pairs of students where commits appear in similar order within close time windows (e.g. student B consistently commits similar content ~T seconds after student A)

2. **Semantic similarity**: for temporally close commits, compute cosine similarity on TF-IDF or bag-of-words representation of diff text. High similarity → suspicious.

3. **Structural similarity**: compare function/variable names extracted from diffs via regex or AST parsing. Similar naming patterns → suspicious.

Output: similarity matrix M[i][j] = combined confidence score (0–1) for each student pair. Build graph: nodes = students, edge weight = M[i][j], only include edges above threshold.

## Acceptance criteria
- [x] Cosine similarity computed correctly for sample diffs
- [x] Sequential correlation detects consistent time-lag patterns between two students
- [x] Combined score M computed as weighted average of three metrics (weights configurable)
- [x] Graph structure returned: `{nodes: [...], edges: [{student_a, student_b, score, details}]}`
- [x] Analysis completes in reasonable time for group of 30 students

## Notes
Blocked by TASK-006. Use `scikit-learn` for TF-IDF + cosine similarity. Structural analysis can use regex for MVP (no full AST parser required).
