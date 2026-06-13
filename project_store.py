from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).with_name("projects.db")


class ProjectStoreError(RuntimeError):
    pass


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_project_store() -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS project_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_history_project_id ON project_history(project_id)"
            )
    except sqlite3.Error as exc:
        raise ProjectStoreError("Could not initialize project database.") from exc


def create_project(user_id: int, name: str, description: str = "") -> dict:
    clean_name = name.strip()
    clean_description = description.strip()
    if not clean_name:
        raise ValueError("Project Name is required.")

    now = utc_now()
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO projects (user_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, clean_name, clean_description, now, now),
            )
            project_id = cursor.lastrowid
    except sqlite3.Error as exc:
        raise ProjectStoreError("Could not create project.") from exc

    return {
        "id": project_id,
        "user_id": user_id,
        "name": clean_name,
        "description": clean_description,
        "created_at": now,
        "updated_at": now,
    }


def list_projects(user_id: int, limit: int = 20) -> list[dict]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, name, description, created_at, updated_at
                FROM projects
                WHERE user_id = ?
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
    except sqlite3.Error as exc:
        raise ProjectStoreError("Could not load projects.") from exc
    return [dict(row) for row in rows]


def get_project(project_id: int, user_id: int) -> dict | None:
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, user_id, name, description, created_at, updated_at
                FROM projects
                WHERE id = ? AND user_id = ?
                LIMIT 1
                """,
                (project_id, user_id),
            ).fetchone()
    except sqlite3.Error as exc:
        raise ProjectStoreError("Could not load project.") from exc
    return dict(row) if row is not None else None


def add_project_history(project_id: int, action_type: str, content: str) -> dict:
    clean_action_type = action_type.strip()
    clean_content = content.strip()
    if not clean_action_type:
        raise ValueError("Action type is required.")
    if not clean_content:
        raise ValueError("History content is required.")

    now = utc_now()
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO project_history (project_id, action_type, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, clean_action_type, clean_content, now),
            )
            connection.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (now, project_id),
            )
            history_id = cursor.lastrowid
    except sqlite3.Error as exc:
        raise ProjectStoreError("Could not save project history.") from exc

    return {
        "id": history_id,
        "project_id": project_id,
        "action_type": clean_action_type,
        "content": clean_content,
        "created_at": now,
    }


def list_project_history(project_id: int, limit: int = 50) -> list[dict]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, action_type, content, created_at
                FROM project_history
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
    except sqlite3.Error as exc:
        raise ProjectStoreError("Could not load project history.") from exc
    return [dict(row) for row in rows]
