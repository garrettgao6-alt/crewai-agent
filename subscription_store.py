from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


DB_PATH = Path(__file__).with_name("users.db")
DEFAULT_TIER = "Starter"
LIMIT_REACHED_MESSAGE = "You have reached your monthly plan limit.\nUpgrade your subscription to continue."

PLAN_CATALOG = {
    "Starter": {
        "price": "$19/month",
        "monthly_request_limit": 100,
        "monthly_document_limit": 20,
        "features": [
            "PDF export",
            "Basic automation templates",
        ],
    },
    "Professional": {
        "price": "$49/month",
        "monthly_request_limit": 1000,
        "monthly_document_limit": 200,
        "features": [
            "Multi-document analysis",
            "Executive Intelligence",
            "Full Automation Intelligence",
        ],
    },
    "Business": {
        "price": "$149/month",
        "monthly_request_limit": 5000,
        "monthly_document_limit": 1000,
        "features": [
            "API access",
            "Team accounts (20 users)",
            "Priority support",
        ],
    },
    "Enterprise": {
        "price": "Custom pricing",
        "monthly_request_limit": None,
        "monthly_document_limit": None,
        "features": [
            "Unlimited*",
            "Dedicated support",
            "Custom deployment",
        ],
    },
}


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_datetime(value: datetime) -> str:
    return value.isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def ensure_subscription_columns(connection: sqlite3.Connection) -> None:
    _ensure_column(connection, "users", "subscription_tier", "TEXT NOT NULL DEFAULT 'Starter'")
    _ensure_column(connection, "users", "monthly_request_limit", "INTEGER DEFAULT 100")
    _ensure_column(connection, "users", "monthly_document_limit", "INTEGER DEFAULT 20")
    _ensure_column(connection, "users", "current_request_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "users", "current_document_count", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "users", "subscription_start", "TEXT")
    _ensure_column(connection, "users", "subscription_end", "TEXT")
    _ensure_column(connection, "users", "stripe_customer_id", "TEXT")
    _ensure_column(connection, "users", "stripe_subscription_id", "TEXT")

    now = utc_now()
    renewal = now + timedelta(days=30)
    connection.execute(
        """
        UPDATE users
        SET subscription_tier = COALESCE(subscription_tier, ?),
            monthly_request_limit = CASE
                WHEN subscription_tier = 'Enterprise' THEN monthly_request_limit
                ELSE COALESCE(monthly_request_limit, ?)
            END,
            monthly_document_limit = CASE
                WHEN subscription_tier = 'Enterprise' THEN monthly_document_limit
                ELSE COALESCE(monthly_document_limit, ?)
            END,
            current_request_count = COALESCE(current_request_count, 0),
            current_document_count = COALESCE(current_document_count, 0),
            subscription_start = COALESCE(subscription_start, ?),
            subscription_end = COALESCE(subscription_end, ?)
        """,
        (
            DEFAULT_TIER,
            PLAN_CATALOG[DEFAULT_TIER]["monthly_request_limit"],
            PLAN_CATALOG[DEFAULT_TIER]["monthly_document_limit"],
            format_datetime(now),
            format_datetime(renewal),
        ),
    )


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def default_subscription_values() -> dict:
    now = utc_now()
    renewal = now + timedelta(days=30)
    plan = PLAN_CATALOG[DEFAULT_TIER]
    return {
        "subscription_tier": DEFAULT_TIER,
        "monthly_request_limit": plan["monthly_request_limit"],
        "monthly_document_limit": plan["monthly_document_limit"],
        "current_request_count": 0,
        "current_document_count": 0,
        "subscription_start": format_datetime(now),
        "subscription_end": format_datetime(renewal),
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
    }


def get_usage(user_id: int) -> dict:
    with get_connection() as connection:
        ensure_subscription_columns(connection)
        _reset_monthly_usage_if_needed(connection, user_id)
        row = connection.execute(
            """
            SELECT
                id,
                subscription_tier,
                monthly_request_limit,
                monthly_document_limit,
                current_request_count,
                current_document_count,
                subscription_start,
                subscription_end,
                stripe_customer_id,
                stripe_subscription_id
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        raise ValueError("User not found.")
    return dict(row)


def can_use_ai_request(user_id: int) -> tuple[bool, str]:
    usage = get_usage(user_id)
    return _can_use(usage["current_request_count"], usage["monthly_request_limit"])


def can_use_document_analysis(user_id: int) -> tuple[bool, str]:
    usage = get_usage(user_id)
    return _can_use(usage["current_document_count"], usage["monthly_document_limit"])


def increment_ai_request(user_id: int) -> dict:
    return _increment_usage(user_id, "current_request_count", "monthly_request_limit")


def increment_document_analysis(user_id: int) -> dict:
    return _increment_usage(user_id, "current_document_count", "monthly_document_limit")


def _can_use(current_count: int, limit: int | None) -> tuple[bool, str]:
    if limit is None:
        return True, ""
    if current_count >= limit:
        return False, LIMIT_REACHED_MESSAGE
    return True, ""


def _increment_usage(user_id: int, count_column: str, limit_column: str) -> dict:
    with get_connection() as connection:
        ensure_subscription_columns(connection)
        _reset_monthly_usage_if_needed(connection, user_id)
        row = connection.execute(
            f"SELECT {count_column}, {limit_column} FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise ValueError("User not found.")

        current_count = row[count_column] or 0
        limit = row[limit_column]
        can_use, message = _can_use(current_count, limit)
        if not can_use:
            raise PermissionError(message)

        connection.execute(
            f"UPDATE users SET {count_column} = {count_column} + 1 WHERE id = ?",
            (user_id,),
        )

    return get_usage(user_id)


def _reset_monthly_usage_if_needed(connection: sqlite3.Connection, user_id: int) -> None:
    row = connection.execute(
        """
        SELECT subscription_tier, subscription_end
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        return

    now = utc_now()
    subscription_end = parse_datetime(row["subscription_end"])
    if subscription_end is not None and subscription_end > now:
        return

    tier = row["subscription_tier"] or DEFAULT_TIER
    plan = PLAN_CATALOG.get(tier, PLAN_CATALOG[DEFAULT_TIER])
    connection.execute(
        """
        UPDATE users
        SET current_request_count = 0,
            current_document_count = 0,
            monthly_request_limit = ?,
            monthly_document_limit = ?,
            subscription_start = ?,
            subscription_end = ?
        WHERE id = ?
        """,
        (
            plan["monthly_request_limit"],
            plan["monthly_document_limit"],
            format_datetime(now),
            format_datetime(now + timedelta(days=30)),
            user_id,
        ),
    )
