from __future__ import annotations

import sqlite3
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

import subscription_store

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None


DB_PATH = Path(__file__).with_name("users.db")
LOCAL_AUTH_PROVIDER = "local"
SUPPORTED_AUTH_PROVIDERS = ("local", "google", "apple")
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 390000
ACCOUNT_LIMIT_REACHED_MESSAGE = "Account limit reached. Please contact the administrator."


class UserStoreError(RuntimeError):
    pass


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_user_store() -> None:
    load_local_environment()
    try:
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'User',
                    created_at TEXT NOT NULL,
                    last_login_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    auth_provider TEXT NOT NULL DEFAULT 'local',
                    provider_user_id TEXT,
                    subscription_tier TEXT NOT NULL DEFAULT 'Starter',
                    monthly_request_limit INTEGER DEFAULT 100,
                    monthly_document_limit INTEGER DEFAULT 20,
                    current_request_count INTEGER NOT NULL DEFAULT 0,
                    current_document_count INTEGER NOT NULL DEFAULT 0,
                    subscription_start TEXT,
                    subscription_end TEXT,
                    stripe_customer_id TEXT,
                    stripe_subscription_id TEXT
                )
                """
            )
            _ensure_column(connection, "users", "email", "TEXT")
            _ensure_column(connection, "users", "role", "TEXT NOT NULL DEFAULT 'User'")
            _ensure_column(connection, "users", "created_at", "TEXT")
            _ensure_column(connection, "users", "last_login_at", "TEXT")
            _ensure_column(connection, "users", "is_active", "INTEGER NOT NULL DEFAULT 1")
            _ensure_column(connection, "users", "auth_provider", "TEXT NOT NULL DEFAULT 'local'")
            _ensure_column(connection, "users", "provider_user_id", "TEXT")
            subscription_store.ensure_subscription_columns(connection)
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
            bootstrap_admin_user(connection)
    except sqlite3.Error as exc:
        raise UserStoreError("Could not initialize user database.") from exc


def load_local_environment() -> None:
    if load_dotenv is not None:
        load_dotenv(Path(__file__).resolve().parent / ".env")


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def get_max_users(default: int = 3) -> int:
    raw_value = os.getenv("MAX_USERS", str(default)).strip()
    try:
        max_users = int(raw_value)
    except ValueError:
        return default
    return max(max_users, 0)


def count_active_users() -> int:
    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS user_count FROM users WHERE is_active = 1"
            ).fetchone()
    except sqlite3.Error as exc:
        raise UserStoreError("Could not read user count.") from exc
    return int(row["user_count"] if row else 0)


def can_create_user(max_users: int = 3) -> bool:
    if max_users == 0:
        return True
    return count_active_users() < max_users


def get_user_limit_status() -> tuple[int, int]:
    """Return active user count and configured maximum user count."""
    return count_active_users(), get_max_users()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, stored_hash = password_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(computed_hash, stored_hash)
    except (AttributeError, TypeError, ValueError):
        return False


def bootstrap_admin_user(connection: sqlite3.Connection) -> None:
    row = connection.execute("SELECT COUNT(*) AS user_count FROM users").fetchone()
    if row is None or int(row["user_count"]) != 0:
        return

    admin_username = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_username or not admin_password:
        return
    if len(admin_password) < 8:
        return

    admin_email = os.getenv("ADMIN_EMAIL", f"{admin_username}@local").strip().lower()
    _insert_user(connection, admin_username, admin_email, admin_password, "Admin")


def create_user(username: str, email: str, password: str, role: str = "User") -> dict:
    clean_username = username.strip()
    clean_email = email.strip().lower()
    clean_role = "Admin" if role == "Admin" else "User"

    if not clean_username:
        raise ValueError("Username is required.")
    if not clean_email or "@" not in clean_email:
        raise ValueError("A valid email is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    max_users = get_max_users()
    if not can_create_user(max_users):
        raise ValueError(ACCOUNT_LIMIT_REACHED_MESSAGE)

    try:
        with get_connection() as connection:
            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE auth_provider = ?
                  AND (lower(username) = ? OR lower(email) = ?)
                LIMIT 1
                """,
                (LOCAL_AUTH_PROVIDER, clean_username.lower(), clean_email),
            ).fetchone()
            if existing_user is not None:
                raise ValueError("Username or email already exists.")

            return _insert_user(connection, clean_username, clean_email, password, clean_role)
    except sqlite3.IntegrityError as exc:
        raise ValueError("Username or email already exists.") from exc
    except sqlite3.Error as exc:
        raise UserStoreError("Could not create account.") from exc


def _insert_user(
    connection: sqlite3.Connection,
    username: str,
    email: str,
    password: str,
    role: str,
) -> dict:
    password_hash = hash_password(password)
    created_at = utc_now()
    subscription_values = subscription_store.default_subscription_values()
    cursor = connection.execute(
                """
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    role,
                    created_at,
                    last_login_at,
                    is_active,
                    auth_provider,
                    provider_user_id,
                    subscription_tier,
                    monthly_request_limit,
                    monthly_document_limit,
                    current_request_count,
                    current_document_count,
                    subscription_start,
                    subscription_end,
                    stripe_customer_id,
                    stripe_subscription_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    email,
                    password_hash,
                    role,
                    created_at,
                    created_at,
                    1,
                    LOCAL_AUTH_PROVIDER,
                    None,
                    subscription_values["subscription_tier"],
                    subscription_values["monthly_request_limit"],
                    subscription_values["monthly_document_limit"],
                    subscription_values["current_request_count"],
                    subscription_values["current_document_count"],
                    subscription_values["subscription_start"],
                    subscription_values["subscription_end"],
                    subscription_values["stripe_customer_id"],
                    subscription_values["stripe_subscription_id"],
                ),
            )
    user_id = cursor.lastrowid
    return {
        "id": user_id,
        "username": username,
        "email": email,
        "role": role,
        "is_active": 1,
        "auth_provider": LOCAL_AUTH_PROVIDER,
        "provider_user_id": None,
        **subscription_values,
        "created_at": created_at,
        "last_login_at": created_at,
    }


def authenticate_user(identifier: str, password: str) -> dict | None:
    clean_identifier = identifier.strip().lower()
    if not clean_identifier or not password:
        return None

    try:
        with get_connection() as connection:
            user_row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE auth_provider = ?
                  AND is_active = 1
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
    except sqlite3.Error as exc:
        raise UserStoreError("Could not sign in.") from exc
