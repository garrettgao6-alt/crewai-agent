from collections.abc import Callable
from typing import Literal, TypedDict


Domain = Literal["construction", "business", "general"]
TaskName = Literal["analysis", "risk", "strategy", "finance", "general"]
Role = Literal["user", "assistant", "system"]


class MemoryEntry(TypedDict):
    role: str
    content: str


AgentExecutor = Callable[[str, str], str]
