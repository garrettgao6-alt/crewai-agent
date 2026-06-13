from core.critic import review_output
from core.memory import Memory
from core.planner import plan_tasks
from core.router import route_task
from core.types import AgentExecutor


memory = Memory()

TASK_DESCRIPTIONS = {
    "analysis": "Perform detailed analysis",
    "risk": "Identify and assess risks",
    "strategy": "Provide strategic recommendations",
}


def build_task_prompt(task: str, prompt: str) -> str:
    task_description = TASK_DESCRIPTIONS.get(task, task)
    history = memory.get(5)
    return f"""Task: {task}
Instruction: {task_description}

User request:
{prompt}

Conversation history:
{history}
"""


def format_task_section(task: str, result: str) -> str:
    section_title = task.replace("_", " ").title()
    return f"--- {section_title} ---\n[Task: {task}]\n{result}"


def run_engine(prompt: str, agent_executor: AgentExecutor) -> str:
    memory.add("user", prompt)

    tasks = plan_tasks(prompt)

    responses = []

    for task in tasks:
        domain = route_task(task)

        task_prompt = build_task_prompt(task, prompt)
        result = agent_executor(domain, task_prompt)

        responses.append(format_task_section(task, result))

    final_output = "\n\n".join(responses)

    final_output = review_output(final_output)

    memory.add("assistant", final_output)

    return final_output
