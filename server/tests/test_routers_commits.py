"""Integration tests for POST /commits endpoint."""

import pytest


@pytest.mark.asyncio
async def test_ingest_commits_success(client, seeded_db):
    token = seeded_db["student_token"]
    res = await client.post(
        "/commits",
        json={"commits": [
            {
                "commit_id": "new001",
                "timestamp": "2026-06-01T09:00:00Z",
                "exercise_id": "ex2",
                "file_name": "main.py",
                "lines_added": 5,
                "lines_removed": 1,
            }
        ]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    assert res.json()["inserted"] == 1


@pytest.mark.asyncio
async def test_ingest_commits_duplicate_ignored(client, seeded_db):
    """Same commit_id+student+file silently ignored, count = 0."""
    token = seeded_db["student_token"]
    # Already seeded: commit_id="abc123", file_name="solution.py"
    res = await client.post(
        "/commits",
        json={"commits": [
            {
                "commit_id": "abc123",
                "timestamp": "2026-06-01T08:05:00Z",
                "exercise_id": "ex1",
                "file_name": "solution.py",
                "lines_added": 10,
                "lines_removed": 2,
            }
        ]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    assert res.json()["inserted"] == 0


@pytest.mark.asyncio
async def test_ingest_commits_with_diff(client, seeded_db):
    """diff field stored without error."""
    token = seeded_db["student_token"]
    res = await client.post(
        "/commits",
        json={"commits": [
            {
                "commit_id": "diff001",
                "timestamp": "2026-06-01T09:10:00Z",
                "exercise_id": "ex1",
                "file_name": "algo.py",
                "lines_added": 3,
                "lines_removed": 0,
                "diff": "+def solve():\n+    return 42\n",
            }
        ]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    assert res.json()["inserted"] == 1


@pytest.mark.asyncio
async def test_ingest_commits_requires_student(client, seeded_db):
    token = seeded_db["teacher_token"]
    res = await client.post(
        "/commits",
        json={"commits": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_ingest_commits_no_token(client):
    res = await client.post("/commits", json={"commits": []})
    assert res.status_code in (401, 403)
