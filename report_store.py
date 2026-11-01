from core.storage_lock import Connection as SnapshotConnection
"""Project-authorized, append-only report snapshots."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import project_store

DB_PATH = Path(__file__).with_name("reports.db")


def _connect():
    connection = sqlite3.connect(DB_PATH, timeout=30, factory=SnapshotConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, project_id INTEGER NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
    connection.execute("CREATE INDEX IF NOT EXISTS reports_scope ON reports(user_id,project_id,created_at)")
    return connection


def save_report(user_id, project_id, entry, *, report_id=None):
    project_store.require_project_access(user_id, project_id)
    payload = dict(entry)
    payload.update(id=report_id or uuid4().hex, user_id=int(user_id), project_id=int(project_id), created_at=datetime.now(timezone.utc).isoformat())
    connection = _connect()
    try:
        with connection:
            connection.execute("INSERT OR IGNORE INTO reports VALUES (?,?,?,?,?)", (payload['id'], int(user_id), int(project_id), payload['created_at'], json.dumps(payload, ensure_ascii=False)))
    finally:
        connection.close()
    return get_report(user_id, project_id, payload["id"])


def list_reports(user_id, project_id, limit=100):
    project_store.require_project_access(user_id, project_id)
    connection = _connect()
    try:
        rows = connection.execute("SELECT payload FROM reports WHERE user_id=? AND project_id=? ORDER BY created_at DESC LIMIT ?", (int(user_id), int(project_id), min(max(int(limit), 1), 1000))).fetchall()
        return [json.loads(row['payload']) for row in rows]
    finally:
        connection.close()


def get_report(user_id, project_id, report_id):
    project_store.require_project_access(user_id, project_id)
    connection = _connect()
    try:
        row = connection.execute("SELECT payload FROM reports WHERE id=? AND user_id=? AND project_id=?", (report_id, int(user_id), int(project_id))).fetchone()
        return json.loads(row['payload']) if row else None
    finally:
        connection.close()


def list_report_summaries(user_id,project_id,*,category=None,limit=1000):
    """List bounded metadata without loading every saved model's issue payload."""
    project_store.require_project_access(user_id,project_id)
    connection=_connect()
    try:
        sql="SELECT id,created_at,json_extract(payload,'$.query') AS query FROM reports WHERE user_id=? AND project_id=? AND json_valid(payload)"
        args=[int(user_id),int(project_id)]
        if category is not None:sql+=" AND json_extract(payload,'$.category')=?";args.append(str(category))
        sql+=' ORDER BY created_at DESC LIMIT ?';args.append(min(max(int(limit),1),1000))
        return [dict(row) for row in connection.execute(sql,args)]
    finally:connection.close()
