# GTU exam analyzer

A tool for detecting academic dishonesty by analysing git commit patterns during exams.

## Repository layout

```
/
├── server/        # FastAPI backend
├── client/        # PyQt6 desktop client
├── db/            # Database schema and migrations
└── docs/          # Project documentation
```

---

## server — FastAPI backend

### Requirements
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Install dependencies

```bash
cd server

# Using uv (recommended)
uv venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e .

# Using pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run the development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment variables

Copy `.env.example` to `.env` and fill in the required values:

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing secret (generate with `openssl rand -hex 32`) |
| `DATABASE_URL` | SQLite async URL, e.g. `sqlite+aiosqlite:///./cheat_buster.db` |

---

## client — PyQt6 desktop application

### Requirements
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- A running instance of the server

### Install dependencies

```bash
cd client

# Using uv (recommended)
uv venv .venv
source .venv/bin/activate  
uv pip install -e .

# Using pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run the client

```bash
python -m app.main
```

### Environment variables

Copy `.env.example` to `.env` inside `client/`:

| Variable | Description |
|---|---|
| `SERVER_URL` | Base URL of the backend, e.g. `http://localhost:8000` |

---

## Database migrations (Alembic)

Alembic is wired to the ORM models. On first run, apply migrations:

```bash
cd server
alembic upgrade head
```

To generate a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

SQLite `render_as_batch=True` is enabled in `env.py` for ALTER TABLE support.

---

## Web dashboard

Teacher dashboard is served at `http://localhost:8000/` by the FastAPI server itself.
No separate frontend build needed. Pages: `/login`, `/dashboard`, `/exams/new`, `/exams/{id}`, `/exams/{id}/report`.

---

## Development notes

- Each package has its own virtual environment (`.venv/`) — do not share them.
- Tests live under `server/tests/` and `client/tests/` respectively.

```bash
# Server tests (60 tests)
cd server && pytest

# Client tests (12 tests)
cd client && pytest tests/

# headless Qt (CI)
QT_QPA_PLATFORM=offscreen pytest client/tests/
```
