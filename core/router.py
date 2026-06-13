def route_task(task: str) -> str:
    mapping = {
        "analysis": "construction",
        "risk": "construction",
        "strategy": "business",
        "finance": "business",
        "general": "general",
    }

    return mapping.get(task, "general")
