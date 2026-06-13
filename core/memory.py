from core.types import MemoryEntry


class Memory:
    def __init__(self):
        self.history: list[MemoryEntry] = []

    def add(self, role, content):
        self.history.append({"role": role, "content": content})

    def get(self, limit=5):
        return self.history[-limit:]

    def clear(self):
        self.history = []
