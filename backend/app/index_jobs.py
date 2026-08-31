from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from app.repository_store import get_connection


_lock = Lock()


def _job_from_row(row) -> dict:
    return {
        "job_id": row[0],
        "repository_id": row[1],
        "status": row[2],
        "stage": row[3],
        "chunk_count": row[4],
        "error": row[5],
        "created_at": row[6].isoformat(),
        "updated_at": row[7].isoformat(),
    }


def create_job(repository_id: str) -> dict:
    """Create or reuse one active indexing job per repository."""
    with _lock:
        connection = get_connection()
        try:
            active = connection.execute(
                """
                SELECT job_id, repository_id, status, stage, chunk_count,
                       error, created_at, updated_at
                FROM index_jobs
                WHERE repository_id = %s
                  AND status IN ('queued', 'running')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (repository_id,),
            ).fetchone()

            if active:
                return _job_from_row(active)

            now = datetime.now(timezone.utc)
            job_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO index_jobs (
                    job_id, repository_id, status, stage,
                    chunk_count, error, created_at, updated_at
                )
                VALUES (%s, %s, 'queued', 'Waiting to start', NULL, NULL, %s, %s)
                """,
                (job_id, repository_id, now, now),
            )
            connection.commit()

            return get_job(job_id)
        finally:
            connection.close()


def get_job(job_id: str) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT job_id, repository_id, status, stage, chunk_count,
                   error, created_at, updated_at
            FROM index_jobs
            WHERE job_id = %s
            """,
            (job_id,),
        ).fetchone()
        return _job_from_row(row) if row else None
    finally:
        connection.close()


def update_job(job_id: str, **updates) -> None:
    allowed_fields = {"status", "stage", "chunk_count", "error"}
    changes = {
        key: value
        for key, value in updates.items()
        if key in allowed_fields
    }
    if not changes:
        return

    changes["updated_at"] = datetime.now(timezone.utc)
    assignments = ", ".join(f"{key} = %s" for key in changes)
    values = [*changes.values(), job_id]

    connection = get_connection()
    try:
        connection.execute(
            f"UPDATE index_jobs SET {assignments} WHERE job_id = %s",
            values,
        )
        connection.commit()
    finally:
        connection.close()


def mark_unfinished_jobs_failed() -> None:
    """Mark jobs from a previous process as interrupted on startup."""
    connection = get_connection()
    try:
        connection.execute(
            """
            UPDATE index_jobs
            SET status = 'failed',
                stage = 'Indexing interrupted',
                error = 'The backend restarted before this job completed.',
                updated_at = %s
            WHERE status IN ('queued', 'running')
            """,
            (datetime.now(timezone.utc),),
        )
        connection.commit()
    finally:
        connection.close()
