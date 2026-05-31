-- cheat-buster: initial schema
-- Migration: 001_initial_schema.sql

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;  -- better concurrent read performance for high-volume commit inserts

-- ─────────────────────────────────────────────
-- Users
-- students: email-only auth (password_hash NULL)
-- teachers: email + bcrypt password_hash
-- ─────────────────────────────────────────────
CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    role          TEXT    NOT NULL CHECK (role IN ('student', 'teacher')),
    password_hash TEXT,              -- NULL for students; bcrypt hash for teachers
    group_number  TEXT,              -- student's academic group (e.g. "108259")
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_users_email ON users(email);

-- ─────────────────────────────────────────────
-- Exams
-- duration_minutes drives JWT TTL: 60 or 120
-- ─────────────────────────────────────────────
CREATE TABLE exams (
    exam_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id       INTEGER NOT NULL REFERENCES users(user_id),
    name             TEXT    NOT NULL,
    group_number     TEXT    NOT NULL,
    exam_date        TEXT    NOT NULL,              -- ISO 8601 date, e.g. "2026-06-01"
    duration_minutes INTEGER NOT NULL DEFAULT 90    -- 60 | 90 | 120; server reads this for JWT exp
        CHECK (duration_minutes > 0),
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_exams_teacher ON exams(teacher_id);

-- ─────────────────────────────────────────────
-- Exam sessions
-- One row per (student, exam). ended_at NULL = still active.
-- variant is the problem set number the student chose.
-- ─────────────────────────────────────────────
CREATE TABLE exam_sessions (
    session_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id     INTEGER NOT NULL REFERENCES exams(exam_id),
    student_id  INTEGER NOT NULL REFERENCES users(user_id),
    variant     INTEGER NOT NULL,
    started_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    ended_at    TEXT,                               -- NULL while session active
    UNIQUE (exam_id, student_id)                   -- one session per student per exam
);

CREATE INDEX idx_sessions_exam ON exam_sessions(exam_id);

-- ─────────────────────────────────────────────
-- Commits  (append-only, high volume)
-- Client sends: commit_id, student_id, timestamp, exercise_id,
--               lines_added, lines_removed, file_name
-- Server enriches with exam_id (from JWT claims).
-- UNIQUE on (commit_id, student_id, file_name) deduplicates retry uploads.
-- ─────────────────────────────────────────────
CREATE TABLE commits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_id     TEXT    NOT NULL,                 -- git SHA or client-generated hash
    student_id    INTEGER NOT NULL REFERENCES users(user_id),
    exam_id       INTEGER NOT NULL REFERENCES exams(exam_id),
    timestamp     TEXT    NOT NULL,                 -- ISO 8601 from client clock
    exercise_id   TEXT    NOT NULL,                 -- exercise/problem identifier within exam
    lines_added   INTEGER NOT NULL DEFAULT 0 CHECK (lines_added   >= 0),
    lines_removed INTEGER NOT NULL DEFAULT 0 CHECK (lines_removed >= 0),
    file_name     TEXT    NOT NULL,
    UNIQUE (commit_id, student_id, file_name)
);

-- Primary analysis query pattern: all commits for an exam, ordered by student + time
CREATE INDEX idx_commits_exam_student_ts ON commits(exam_id, student_id, timestamp);
-- Secondary: timeline per student across exams
CREATE INDEX idx_commits_student_ts      ON commits(student_id, timestamp);

-- ─────────────────────────────────────────────
-- Analysis results  (per-student, per-exam)
-- Cached after post-exam analysis run.
-- UNIQUE ensures one result row per (exam, student); re-analysis overwrites via INSERT OR REPLACE.
-- ─────────────────────────────────────────────
CREATE TABLE analysis_results (
    result_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id          INTEGER NOT NULL REFERENCES exams(exam_id),
    student_id       INTEGER NOT NULL REFERENCES users(user_id),
    normality_score  REAL    NOT NULL,              -- 0.0 (very suspicious) – 1.0 (normal)
    suspicious_flags TEXT,                          -- JSON array, e.g. ["burst","late_start"]
    analyzed_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (exam_id, student_id)
);

CREATE INDEX idx_analysis_exam ON analysis_results(exam_id, normality_score);

-- ─────────────────────────────────────────────
-- Similarity pairs  (per-exam, student A ↔ student B)
-- CHECK (student_a_id < student_b_id) enforces canonical ordering so
-- the pair (A,B) and (B,A) cannot both exist — halves storage, simplifies queries.
-- similarity_score = cumulative metric M summed over all matching commit pairs.
-- details stores per-metric breakdown as JSON for the report drilldown.
-- ─────────────────────────────────────────────
CREATE TABLE similarity_pairs (
    pair_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id          INTEGER NOT NULL REFERENCES exams(exam_id),
    student_a_id     INTEGER NOT NULL REFERENCES users(user_id),
    student_b_id     INTEGER NOT NULL REFERENCES users(user_id),
    similarity_score REAL    NOT NULL CHECK (similarity_score >= 0),
    details          TEXT,                          -- JSON: {cosine, structural, sequential}
    analyzed_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CHECK (student_a_id < student_b_id),
    UNIQUE (exam_id, student_a_id, student_b_id)
);

-- Report query: fetch all pairs for an exam sorted by suspicion level
CREATE INDEX idx_similarity_exam_score ON similarity_pairs(exam_id, similarity_score DESC);
