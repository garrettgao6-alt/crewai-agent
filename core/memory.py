import os
import sqlite3


class Memory:
    def __init__(self):
        db_path = os.getenv("COPILOT_MEMORY_DB", "memory.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY,
                role TEXT,
                content TEXT
            )
            """
        )
        self.conn.commit()

    def _ensure_user_id_column(self):
        columns = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(memory)").fetchall()
        }
        if "user_id" not in columns:
            self.conn.execute("ALTER TABLE memory ADD COLUMN user_id TEXT DEFAULT 'default'")
            self.conn.commit()

    def add(self, *args):
        if len(args) == 2:
            user_id = "default"
            role, content = args
        elif len(args) == 3:
            user_id, role, content = args
        else:
            raise TypeError("add expects (role, content) or (user_id, role, content)")

        self._ensure_user_id_column()
        self.conn.execute(
            "INSERT INTO memory (user_id, role, content) VALUES (?, ?, ?)",
            (str(user_id), role, content),
        )
        self.conn.commit()

    def get(self, user_id="default", limit=5):
        if isinstance(user_id, int):
            limit = user_id
            user_id = "default"

        self._ensure_user_id_column()
        cursor = self.conn.execute(
            "SELECT role, content FROM memory WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (str(user_id), limit),
        )
        return [{"role": role, "content": content} for role, content in cursor.fetchall()][::-1]

    def clear(self, user_id=None):
        self._ensure_user_id_column()
        if user_id is None:
            self.conn.execute("DELETE FROM memory")
        else:
            self.conn.execute("DELETE FROM memory WHERE user_id = ?", (str(user_id),))
        self.conn.commit()
