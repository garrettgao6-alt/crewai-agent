def plan_tasks(prompt: str) -> list:
    tasks = []
    prompt_lower = prompt.lower()

    if "analyze" in prompt_lower:
        tasks.append("analysis")

    if "risk" in prompt_lower:
        tasks.append("risk")

    if "strategy" in prompt_lower:
        tasks.append("strategy")

    if not tasks:
        tasks.append("general")

    return tasks
