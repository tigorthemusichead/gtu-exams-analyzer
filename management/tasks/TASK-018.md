# TASK-018: Interactive similarity graph (web, D3.js)

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
Implement the interactive similarity graph on the report page (`GET /exams/{exam_id}/report`) built in TASK-017. Rendered client-side with D3.js — no server changes needed beyond the existing analysis API.

**Spec requirement:** "Отображается интерактивный граф близости между работами студентов, при клике на ребро графа открывается окно с детальными метриками. Также визуально выделяются рёбра, для которых метрика близости M больше порогового значения."

**Implementation:**

Report page JS fetches `GET /analysis/{exam_id}/report` → receives nodes (students) + edges (similarity pairs with cosine/structural/sequential scores).

D3.js force-directed graph:
- **Node** = student (label: email or ID), colored red if anomaly_score above individual threshold
- **Edge** = similarity pair; width/color encodes combined score M
  - Above threshold (default 0.6): red, thick
  - Below threshold: gray, thin
- **Click edge** → modal/side panel showing:
  - Student A and Student B names
  - Combined score M
  - Breakdown: cosine, structural, sequential scores
- **Threshold slider** → JS re-styles edges in-place (no re-fetch), moves edges above/below cutoff in real time

**Summary panel** (below graph):
- Table: suspect pairs sorted by M descending
- Individual anomaly scores table: all students, score, flagged events

**Files to create:**
- `server/app/web/static/js/report.js` — D3 graph logic
- `server/app/web/static/css/report.css` — graph + modal styles
- `server/app/web/templates/report.html` — report page template (extends base)

## Acceptance criteria
- [ ] Force-directed graph renders all students as nodes
- [ ] Edges above threshold visually distinct (red/thick) from edges below (gray/thin)
- [ ] Clicking edge opens detail panel with cosine/structural/sequential scores and student names
- [ ] Threshold slider re-styles graph in real time without page reload
- [ ] Individual anomaly summary table shows all students with scores and event counts
- [ ] Graph is responsive (fits container width)

## Notes
Load D3.js v7 from CDN (`<script src="https://cdn.jsdelivr.net/npm/d3@7">`). No npm/build needed.
Edge click: use D3 `.on("click", ...)` handler. Modal: plain HTML `<dialog>` element.
If `GroupAnalysisResult` returns all edges (not just above threshold), slider works entirely client-side — preferred.
Update `routers/analysis.py` to return all pairs (score ≥ 0) not just pairs above threshold, so slider has full data.
