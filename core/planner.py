import json
import os

from openai import OpenAI


PLANNER_MODEL = os.getenv("OPENAI_PLANNER_MODEL", "gpt-4o-mini")
ALLOWED_TASKS = {"analysis", "risk", "strategy", "finance", "general"}


def _get_client() -> OpenAI:
    return OpenAI()


def _fallback_plan_tasks(prompt: str) -> list:
    tasks = []
    prompt_lower = prompt.lower()

    if "analyze" in prompt_lower or "analysis" in prompt_lower:
        tasks.append("analysis")

    if "risk" in prompt_lower:
        tasks.append("risk")

    if "strategy" in prompt_lower:
        tasks.append("strategy")

    if "finance" in prompt_lower or "revenue" in prompt_lower:
        tasks.append("finance")

    if not tasks:
        tasks.append("general")

    return tasks


def _validate_tasks(tasks: list) -> list:
    validated_tasks = []
    for task in tasks:
        normalized_task = str(task).strip().lower()
        if normalized_task in ALLOWED_TASKS and normalized_task not in validated_tasks:
            validated_tasks.append(normalized_task)

    return validated_tasks or ["general"]


def plan_tasks(prompt: str) -> list:
    try:
        client = _get_client()
        response = client.responses.create(
            model=PLANNER_MODEL,
            input=[
                {
                    "role": "system",
                    "content": """
You are a task planner.

Break the user request into tasks.

Allowed tasks:

* analysis
* risk
* strategy
* finance
* general

Return JSON only:
{"tasks": ["analysis", "risk"]}
""",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        data = json.loads(response.output_text)
        return _validate_tasks(data.get("tasks", ["general"]))
    except Exception:
        return _fallback_plan_tasks(prompt)
