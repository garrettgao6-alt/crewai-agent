from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import bcrypt


DB_PATH = Path(__file__).with_name("users.db")
LOCAL_AUTH_PROVIDER = "local"
SUPPORTED_AUTH_PROVIDERS = ("local", "google", "apple")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_user_store() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'User',
                auth_provider TEXT NOT NULL DEFAULT 'local',
                provider_user_id TEXT,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
        _ensure_column(connection, "users", "email", "TEXT")
        _ensure_column(connection, "users", "role", "TEXT NOT NULL DEFAULT 'User'")
        _ensure_column(connection, "users", "auth_provider", "TEXT NOT NULL DEFAULT 'local'")
        _ensure_column(connection, "users", "provider_user_id", "TEXT")
        _ensure_column(connection, "users", "created_at", "TEXT")
        _ensure_column(connection, "users", "last_login_at", "TEXT")
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_provider
            ON users (username, auth_provider)
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_provider
            ON users (email, auth_provider)
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_user_id
            ON users (auth_provider, provider_user_id)
            WHERE provider_user_id IS NOT NULL
            """
        )


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_user(username: str, email: str, password: str) -> dict:
    clean_username = username.strip()
    clean_email = email.strip().lower()

    if not clean_username:
        raise ValueError("Username is required.")
    if not clean_email or "@" not in clean_email:
        raise ValueError("A valid email is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    password_hash = hash_password(password)
    created_at = utc_now()

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    role,
                    auth_provider,
                    provider_user_id,
                    created_at,
                    last_login_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_username,
                    clean_email,
                    password_hash,
                    "User",
                    LOCAL_AUTH_PROVIDER,
                    None,
                    created_at,
                    created_at,
                ),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError("Username or email already exists.") from exc

    return {
        "id": user_id,
        "username": clean_username,
        "email": clean_email,
        "role": "User",
        "auth_provider": LOCAL_AUTH_PROVIDER,
        "provider_user_id": None,
        "created_at": created_at,
        "last_login_at": created_at,
    }


def authenticate_user(identifier: str, password: str) -> dict | None:
    clean_identifier = identifier.strip().lower()
    if not clean_identifier or not password:
        return None

    with get_connection() as connection:
        user_row = connection.execute(
            """
            SELECT *
            FROM users
            WHERE auth_provider = ?
              AND (lower(username) = ? OR lower(email) = ?)
            LIMIT 1
            """,
            (LOCAL_AUTH_PROVIDER, clean_identifier, clean_identifier),
        ).fetchone()

        if user_row is None:
            return None

        user = dict(user_row)
        if not verify_password(password, user["password_hash"]):
            return None

        last_login_at = utc_now()
        connection.execute(
            "UPDATE users SET last_login_at = ? WHERE id = ?",
            (last_login_at, user["id"]),
        )
        user["last_login_at"] = last_login_at
        user.pop("password_hash", None)
        return user
