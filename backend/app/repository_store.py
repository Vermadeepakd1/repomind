import os

from datetime import datetime, timezone

import psycopg
from uuid import uuid4
from psycopg.types.json import Json

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
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                repository_id TEXT PRIMARY KEY,
                repo_url TEXT NOT NULL UNIQUE,
                repo_name TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                indexed_at TIMESTAMPTZ NOT NULL,
                user_id TEXT REFERENCES users(user_id)
            )
            """
        )

        connection.execute(
            "ALTER TABLE repositories ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(user_id)"
        )

        connection.execute(
            "ALTER TABLE repositories DROP CONSTRAINT IF EXISTS repositories_repo_url_key"
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS repositories_user_url_idx
            ON repositories (user_id, repo_url)
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS index_jobs (
                job_id TEXT PRIMARY KEY,
                repository_id TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                chunk_count INTEGER,
                error TEXT,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS index_jobs_repository_status_idx
            ON index_jobs (repository_id, status)
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                chat_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                repository_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'New chat',
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id BIGSERIAL PRIMARY KEY,
                chat_id TEXT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ NOT NULL
            )
            """
        )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS chats_owner_repository_idx ON chats (user_id, repository_id, updated_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS chat_messages_chat_idx ON chat_messages (chat_id, created_at)"
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS repository_files (
                repository_id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                line_count INTEGER NOT NULL,
                byte_size INTEGER NOT NULL,
                PRIMARY KEY (repository_id, file_path)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS repository_files_owner_idx ON repository_files (user_id, repository_id)"
        )

        connection.commit()

    finally:
        connection.close()


def save_repository(
    repository_id: str,
    repo_url: str,
    repo_name: str,
    chunk_count: int,
    user_id: str | None = None,
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
                indexed_at,
                user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)

            ON CONFLICT(repository_id)
            DO UPDATE SET
                repo_url = EXCLUDED.repo_url,
                repo_name = EXCLUDED.repo_name,
                chunk_count = EXCLUDED.chunk_count,
                indexed_at = EXCLUDED.indexed_at,
                user_id = EXCLUDED.user_id
            """,
            (
                repository_id,
                repo_url,
                repo_name,
                chunk_count,
                indexed_at,
                user_id,
            )
        )

        connection.commit()

    finally:
        connection.close()


def get_repositories(user_id: str | None = None):

    connection = get_connection()

    try:

        if user_id:
            rows = connection.execute(
                """
                SELECT repository_id, repo_url, repo_name, chunk_count, indexed_at
                FROM repositories
                WHERE user_id = %s
                ORDER BY indexed_at DESC
                """,
                (user_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT repository_id, repo_url, repo_name, chunk_count, indexed_at
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


def create_user(email: str, password_hash: str):
    connection = get_connection()
    try:
        user_id = str(uuid4())
        connection.execute(
            "INSERT INTO users (user_id, email, password_hash, created_at) VALUES (%s, %s, %s, %s)",
            (user_id, email, password_hash, datetime.now(timezone.utc)),
        )
        connection.commit()
        return {"user_id": user_id, "email": email}
    finally:
        connection.close()


def get_user_by_email(email: str):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT user_id, email, password_hash FROM users WHERE email = %s",
            (email,),
        ).fetchone()
        return {"user_id": row[0], "email": row[1], "password_hash": row[2]} if row else None
    finally:
        connection.close()


def get_user_by_id(user_id: str):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT user_id, email FROM users WHERE user_id = %s", (user_id,)
        ).fetchone()
        return {"user_id": row[0], "email": row[1]} if row else None
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


def repository_belongs_to_user(repository_id: str, user_id: str) -> bool:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT 1 FROM repositories WHERE repository_id = %s AND user_id = %s",
            (repository_id, user_id),
        ).fetchone()
        return bool(row)
    finally:
        connection.close()


def create_chat(user_id: str, repository_id: str, title: str = "New chat"):
    connection = get_connection()
    try:
        chat_id = str(uuid4())
        now = datetime.now(timezone.utc)
        connection.execute(
            """
            INSERT INTO chats (chat_id, user_id, repository_id, title, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (chat_id, user_id, repository_id, title, now, now),
        )
        connection.commit()
        return {
            "chat_id": chat_id,
            "repository_id": repository_id,
            "title": title,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    finally:
        connection.close()


def get_chats(user_id: str, repository_id: str):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT chat_id, repository_id, title, created_at, updated_at
            FROM chats
            WHERE user_id = %s AND repository_id = %s
            ORDER BY updated_at DESC
            """,
            (user_id, repository_id),
        ).fetchall()
        return [
            {
                "chat_id": row[0],
                "repository_id": row[1],
                "title": row[2],
                "created_at": row[3].isoformat(),
                "updated_at": row[4].isoformat(),
            }
            for row in rows
        ]
    finally:
        connection.close()


def get_chat(chat_id: str, user_id: str):
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT chat_id, repository_id, title, created_at, updated_at
            FROM chats
            WHERE chat_id = %s AND user_id = %s
            """,
            (chat_id, user_id),
        ).fetchone()
        if not row:
            return None
        return {
            "chat_id": row[0],
            "repository_id": row[1],
            "title": row[2],
            "created_at": row[3].isoformat(),
            "updated_at": row[4].isoformat(),
        }
    finally:
        connection.close()


def get_chat_messages(chat_id: str, user_id: str):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT message_id, role, content, sources, created_at
            FROM chat_messages
            WHERE chat_id = %s
              AND EXISTS (SELECT 1 FROM chats WHERE chat_id = %s AND user_id = %s)
            ORDER BY created_at ASC, message_id ASC
            """,
            (chat_id, chat_id, user_id),
        ).fetchall()
        return [
            {
                "message_id": row[0],
                "role": row[1],
                "content": row[2],
                "sources": row[3] or [],
                "created_at": row[4].isoformat(),
            }
            for row in rows
        ]
    finally:
        connection.close()


def add_chat_message(chat_id: str, role: str, content: str, sources: list | None = None):
    connection = get_connection()
    try:
        now = datetime.now(timezone.utc)
        connection.execute(
            """
            INSERT INTO chat_messages (chat_id, role, content, sources, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (chat_id, role, content, Json(sources or []), now),
        )
        connection.execute(
            "UPDATE chats SET updated_at = %s WHERE chat_id = %s",
            (now, chat_id),
        )
        connection.commit()
    finally:
        connection.close()


def save_repository_files(repository_id: str, user_id: str, files: list):
    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM repository_files WHERE repository_id = %s AND user_id = %s",
            (repository_id, user_id),
        )
        for file in files:
            content = file["content"]
            connection.execute(
                """
                INSERT INTO repository_files (repository_id, user_id, file_path, line_count, byte_size)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    repository_id,
                    user_id,
                    file["path"],
                    len(content.splitlines()),
                    len(content.encode("utf-8")),
                ),
            )
        connection.commit()
    finally:
        connection.close()


def get_repository_files(repository_id: str, user_id: str):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT file_path, line_count, byte_size
            FROM repository_files
            WHERE repository_id = %s AND user_id = %s
            ORDER BY file_path ASC
            """,
            (repository_id, user_id),
        ).fetchall()
        return [
            {"path": row[0], "line_count": row[1], "byte_size": row[2]}
            for row in rows
        ]
    finally:
        connection.close()
