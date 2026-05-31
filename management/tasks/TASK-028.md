# TASK-028: Suspect pair similarity detail modal (table row + graph edge)

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
Two entry points must open the same modal showing what code snippets the system flagged as similar between two students:

1. Clicking a row in the suspect pairs table
2. Clicking an edge (connection line) between two nodes in the D3 similarity graph

The modal must show the matched/similar code segments side-by-side with similarity scores per component (cosine, structural, sequential).

## Acceptance criteria
- [ ] Clicking a suspect pairs table row opens the detail modal for that pair
- [ ] Clicking an edge in the D3 graph opens the same detail modal for that pair
- [ ] Modal displays both student identifiers (emails after TASK-026)
- [ ] Modal shows overall similarity score and breakdown: cosine, structural, sequential component scores
- [ ] Modal shows matched code snippets or token sequences that drove the similarity score (from `SimilarityPair.details` JSON)
- [ ] Both entry points call the same modal function with the same data shape
- [ ] Modal has close button, backdrop-click close, and Escape key close
- [ ] If details JSON lacks snippet data, modal shows scores only with a note

## Notes
- `SimilarityPair.details` stores JSON with keys: `cosine`, `structural`, `sequential` (and possibly matched snippet lists)
- Inspect actual `details` JSON structure in `analysis_group.py` to confirm what snippet data is available
- D3 graph already has a `showModal()` called on edge click (`report.js` lines ~121-133) — extend this rather than replacing
- Suspect pairs table currently built by `renderSuspectPairs()` in `report.js` lines ~136-158 — add click handler there
- If `details` doesn't currently store raw snippets, may need to update `analysis_group.py` to capture and persist them
