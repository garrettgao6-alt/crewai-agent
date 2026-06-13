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

NCC_LEGAL_PROMPT = """You are a construction compliance expert.

You MUST:
* only use provided NCC context
* cite clause numbers
* do NOT guess

If unsure, say:
'Insufficient NCC reference found.'

Mandatory output format:
Compliance Summary
Relevant Clauses
* C3.2
* C3.3
Assessment
Risk Level"""


def build_task_prompt(
    task: str,
    prompt: str,
    context: str = "",
    sources: str = "",
    legal_mode: bool = False,
) -> str:
    task_description = TASK_DESCRIPTIONS.get(task, task)
    history = memory.get(5)
    resolved_context = context or "Insufficient data"
    resolved_sources = sources or "No retrieved sources"
    legal_prompt = f"\nLegal mode system prompt:\n{NCC_LEGAL_PROMPT}\n" if legal_mode else ""
    return f"""Task: {task}
Instruction: {task_description}
{legal_prompt}

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
    legal_mode = bool(retrieval.get("legal_mode"))

    responses = []

    for task in tasks:
        domain = route_task(task)

        task_prompt = build_task_prompt(task, prompt, context, sources, legal_mode=legal_mode)
        result = agent_executor(domain, task_prompt)
        result = ensure_citations(result, sources)

        responses.append(format_task_section(task, result))

    final_output = "\n\n".join(responses)

    final_output = review_output(final_output)

    memory.add("assistant", final_output)

    return final_output
