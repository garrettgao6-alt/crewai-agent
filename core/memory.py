import os
import sqlite3
from threading import RLock


class Memory:
    def __init__(self):
        self.lock = RLock()
        self.conn = sqlite3.connect(os.getenv("COPILOT_MEMORY_DB", "memory.db"), check_same_thread=False, timeout=30)
        with self.lock, self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY, role TEXT, content TEXT)")
            columns = {row[1] for row in self.conn.execute("PRAGMA table_info(memory)")}
            if "user_id" not in columns:
                self.conn.execute("ALTER TABLE memory ADD COLUMN user_id TEXT DEFAULT 'default'")

    def add(self, *args):
        if len(args) == 2:
            user_id, role, content = "default", *args
        elif len(args) == 3:
            user_id, role, content = args
        else:
            raise TypeError("add expects (role, content) or (user_id, role, content)")
        with self.lock, self.conn:
            self.conn.execute("INSERT INTO memory (user_id,role,content) VALUES (?,?,?)", (str(user_id),role,content))

    def get(self, user_id="default", limit=5):
        with self.lock:
            rows = self.conn.execute("SELECT role,content FROM memory WHERE user_id=? ORDER BY id DESC LIMIT ?", (str(user_id),limit)).fetchall()
        return [{"role":role,"content":content} for role,content in rows][::-1]

    def clear(self, user_id=None):
        with self.lock, self.conn:
            if user_id is None:
                self.conn.execute("DELETE FROM memory")
            else:
                self.conn.execute("DELETE FROM memory WHERE user_id=?", (str(user_id),))
