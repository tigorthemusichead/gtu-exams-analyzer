# Kanban — cheat-buster project tracker

MD-based kanban. Board: `management/board.md`. Tasks: `management/tasks/TASK-NNN.md`.

## Commands

### /kanban add <title>
Create new task in Backlog.
1. Find next ID: count files in `management/tasks/`, increment.
2. Create `management/tasks/TASK-NNN.md` from template below.
3. Append entry to Backlog column in `management/board.md`.

### /kanban move <TASK-NNN> <column>
Move task to column. Columns: `backlog` | `in-progress` | `done`.
1. Remove entry from current column in `board.md`.
2. Add entry to target column in `board.md`.
3. Update `status:` field in task file.

### /kanban show <TASK-NNN>
Read and display `management/tasks/TASK-NNN.md`.

### /kanban list [column]
Display board or single column from `board.md`.

### /kanban edit <TASK-NNN>
Read task file, apply requested changes, write back.

### /kanban done <TASK-NNN>
Shorthand for `/kanban move <TASK-NNN> done`.

## Task file template

```markdown
# TASK-NNN: <title>

status: backlog
created: YYYY-MM-DD
updated: YYYY-MM-DD

## Description
<what needs to be done>

## Acceptance criteria
- [ ] ...

## Notes
```

## Board format

`management/board.md` uses three H2 sections. Each task is one line:
```
- [TASK-NNN] Title
```

Never reorder tasks within a column except to move them. Preserve all other lines verbatim.

## Rules
- IDs are sequential, never reused.
- Status in task file must match column in board. Keep in sync on every move.
- `updated:` field changes on every edit or move.
