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

    def add(self, role, content):
        self.conn.execute(
            "INSERT INTO memory (role, content) VALUES (?, ?)",
            (role, content),
        )
        self.conn.commit()

    def get(self, limit=5):
        cursor = self.conn.execute(
            "SELECT role, content FROM memory ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [{"role": role, "content": content} for role, content in cursor.fetchall()][::-1]

    def clear(self):
        self.conn.execute("DELETE FROM memory")
        self.conn.commit()
