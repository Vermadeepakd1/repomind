import os

from datetime import datetime, timezone

import psycopg

from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set"
    )


def get_connection():
    return psycopg.connect(
        DATABASE_URL
    )


def init_database():

    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                repository_id TEXT PRIMARY KEY,
                repo_url TEXT NOT NULL UNIQUE,
                repo_name TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                indexed_at TIMESTAMPTZ NOT NULL
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


def save_repository(
    repository_id: str,
    repo_url: str,
    repo_name: str,
    chunk_count: int
):

    connection = get_connection()

    try:

        indexed_at = datetime.now(
            timezone.utc
        )

        connection.execute(
            """
            INSERT INTO repositories (
                repository_id,
                repo_url,
                repo_name,
                chunk_count,
                indexed_at
            )
            VALUES (%s, %s, %s, %s, %s)

            ON CONFLICT(repository_id)
            DO UPDATE SET
                repo_url = EXCLUDED.repo_url,
                repo_name = EXCLUDED.repo_name,
                chunk_count = EXCLUDED.chunk_count,
                indexed_at = EXCLUDED.indexed_at
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

    finally:
        connection.close()


def get_repositories():

    connection = get_connection()

    try:

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

        return [
            {
                "repository_id": row[0],
                "repo_url": row[1],
                "repo_name": row[2],
                "chunk_count": row[3],
                "indexed_at": row[4].isoformat(),
            }
            for row in rows
        ]

    finally:
        connection.close()


def get_repository(
    repository_id: str
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                repository_id,
                repo_url,
                repo_name,
                chunk_count,
                indexed_at
            FROM repositories
            WHERE repository_id = %s
            """,
            (
                repository_id,
            )
        ).fetchone()

        if not row:
            return None

        return {
            "repository_id": row[0],
            "repo_url": row[1],
            "repo_name": row[2],
            "chunk_count": row[3],
            "indexed_at": row[4].isoformat(),
        }

    finally:
        connection.close()