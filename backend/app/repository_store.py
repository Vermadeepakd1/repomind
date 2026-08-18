import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DATABASE_PATH = Path("repomind.db")


def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS repositories (
            repository_id TEXT PRIMARY KEY,
            repo_url TEXT NOT NULL UNIQUE,
            repo_name TEXT NOT NULL,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            indexed_at TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()


def save_repository(
    repository_id: str,
    repo_url: str,
    repo_name: str,
    chunk_count: int
):

    connection = get_connection()

    indexed_at = datetime.now(
        timezone.utc
    ).isoformat()

    connection.execute(
        """
        INSERT INTO repositories (
            repository_id,
            repo_url,
            repo_name,
            chunk_count,
            indexed_at
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(repository_id)
        DO UPDATE SET
            repo_url = excluded.repo_url,
            repo_name = excluded.repo_name,
            chunk_count = excluded.chunk_count,
            indexed_at = excluded.indexed_at
        """,
        (
            repository_id,
            repo_url,
            repo_name,
            chunk_count,
            indexed_at,
        )
    )

    connection.commit()
    connection.close()


def get_repositories():

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            repository_id,
            repo_url,
            repo_name,
            chunk_count,
            indexed_at
        FROM repositories
        ORDER BY indexed_at DESC
        """
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


def get_repository(
    repository_id: str
):

    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            repository_id,
            repo_url,
            repo_name,
            chunk_count,
            indexed_at
        FROM repositories
        WHERE repository_id = ?
        """,
        (repository_id,)
    ).fetchone()

    connection.close()

    if not row:
        return None

    return dict(row)