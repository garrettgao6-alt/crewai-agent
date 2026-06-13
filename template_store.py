from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).with_name("templates.db")
TEMPLATE_CATEGORIES = [
    "Construction",
    "Marketing",
    "Business",
    "Automation",
    "Data Analysis",
]

DEFAULT_TEMPLATES = [
    {
        "name": "Construction Proposal Review",
        "description": "Analyze construction proposals for scope gaps, commercial risk, and next actions.",
        "category": "Construction",
        "price": 0,
        "config": {
            "automation_type": "Document Review Workflow",
            "output": "Construction proposal analysis",
            "steps": ["Extract scope", "Identify risks", "Create action list"],
        },
    },
    {
        "name": "Marketing Strategy Builder",
        "description": "Generate a structured marketing strategy brief for a campaign or offer.",
        "category": "Marketing",
        "price": 0,
        "config": {
            "automation_type": "Marketing Strategy Workflow",
            "output": "Campaign strategy brief",
            "steps": ["Define audience", "Map channels", "Draft launch plan"],
        },
    },
    {
        "name": "Executive Business Review",
        "description": "Create an executive summary with risks, opportunities, and recommendations.",
        "category": "Business",
        "price": 0,
        "config": {
            "automation_type": "Executive Review Workflow",
            "output": "Board-ready summary",
            "steps": ["Summarize inputs", "Score risks", "Recommend decisions"],
        },
    },
    {
        "name": "Project Workflow Automation",
        "description": "Convert a project process into a repeatable automation blueprint.",
        "category": "Automation",
        "price": 0,
        "config": {
            "automation_type": "Project Workflow System",
            "output": "Automation blueprint",
            "steps": ["Map triggers", "Assign owners", "Define reporting cadence"],
        },
    },
    {
        "name": "Data Analysis Starter",
        "description": "Build a first-pass data analysis plan with metrics, checks, and outputs.",
        "category": "Data Analysis",
        "price": 0,
        "config": {
            "automation_type": "Data Analysis Workflow",
            "output": "Analysis plan",
            "steps": ["Validate dataset", "Define metrics", "Create findings report"],
        },
    },
    {
        "name": "Premium Tender Intelligence Pack",
        "description": "Advanced tender review workflow with commercial, compliance, and executive checks.",
        "category": "Construction",
        "price": 49,
        "config": {
            "automation_type": "Premium Tender Intelligence",
            "output": "Tender intelligence pack",
            "steps": ["Deep tender review", "Risk scoring", "Board recommendation"],
        },
    },
]


class TemplateStoreError(RuntimeError):
    pass


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_template_store() -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL DEFAULT 0,
                    config_json TEXT NOT NULL,
                    is_public INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category)"
            )
            seed_default_templates(connection)
    except sqlite3.Error as exc:
        raise TemplateStoreError("Could not initialize template database.") from exc


def seed_default_templates(connection: sqlite3.Connection) -> None:
    row = connection.execute("SELECT COUNT(*) AS template_count FROM templates").fetchone()
    if row is not None and int(row["template_count"]) > 0:
        return

    created_at = utc_now()
    for template in DEFAULT_TEMPLATES:
        connection.execute(
            """
            INSERT INTO templates (
                name,
                description,
                category,
                price,
                config_json,
                is_public,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template["name"],
                template["description"],
                template["category"],
                template["price"],
                json.dumps(template["config"], indent=2),
                1,
                created_at,
            ),
        )


def list_templates(category: str | None = None, search: str = "", limit: int = 50) -> list[dict]:
    filters = ["is_public = 1"]
    values: list[object] = []

    if category and category != "All":
        filters.append("category = ?")
        values.append(category)

    clean_search = search.strip().lower()
    if clean_search:
        filters.append("(lower(name) LIKE ? OR lower(description) LIKE ?)")
        values.extend([f"%{clean_search}%", f"%{clean_search}%"])

    values.append(limit)
    where_clause = " AND ".join(filters)
    try:
        with get_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT id, name, description, category, price, config_json, is_public, created_at
                FROM templates
                WHERE {where_clause}
                ORDER BY price ASC, created_at DESC, id ASC
                LIMIT ?
                """,
                values,
            ).fetchall()
    except sqlite3.Error as exc:
        raise TemplateStoreError("Could not load templates.") from exc
    return [dict(row) for row in rows]


def get_template(template_id: int) -> dict | None:
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, name, description, category, price, config_json, is_public, created_at
                FROM templates
                WHERE id = ? AND is_public = 1
                LIMIT 1
                """,
                (template_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise TemplateStoreError("Could not load template.") from exc
    return dict(row) if row is not None else None
