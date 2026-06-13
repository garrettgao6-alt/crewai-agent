from core.critic import review_output
from core.memory import Memory
from core.planner import plan_tasks
from core.retriever import retrieve_context
from core.router import route_task
from core.types import AgentExecutor


memory = Memory()

TASK_DESCRIPTIONS = {
    "analysis": "Perform detailed analysis",
    "risk": "Identify and assess risks",
    "strategy": "Provide strategic recommendations",
}


def build_task_prompt(task: str, prompt: str, context: str = "", sources: str = "") -> str:
    task_description = TASK_DESCRIPTIONS.get(task, task)
    history = memory.get(5)
    resolved_context = context or "Insufficient data"
    resolved_sources = sources or "No retrieved sources"
    return f"""Task: {task}
Instruction: {task_description}

Context:
{resolved_context}

User request:
{prompt}

Conversation history:
{history}

You must ONLY use the provided context.
If not enough information, say 'Insufficient data'.

Output format:
Answer
Sources:
{resolved_sources}
"""


def format_task_section(task: str, result: str) -> str:
    section_title = task.replace("_", " ").title()
    return f"--- {section_title} ---\n[Task: {task}]\n{result}"


def ensure_citations(result: str, sources: str) -> str:
    if not sources or "Sources:" in result:
        return result
    return f"{result}\n\nSources:\n{sources}"


def run_engine(prompt: str, agent_executor: AgentExecutor, user_id: str = "default") -> str:
    memory.add("user", prompt)

    tasks = plan_tasks(prompt)
    retrieval = retrieve_context(prompt, user_id=user_id)
    context = retrieval["context"]
    sources = retrieval["sources"]

    responses = []

    for task in tasks:
        domain = route_task(task)

        task_prompt = build_task_prompt(task, prompt, context, sources)
        result = agent_executor(domain, task_prompt)
        result = ensure_citations(result, sources)

        responses.append(format_task_section(task, result))

    final_output = "\n\n".join(responses)

    final_output = review_output(final_output)

    memory.add("assistant", final_output)

    return final_output
