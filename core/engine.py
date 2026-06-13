from core.critic import review_output
from core.memory import Memory
from core.planner import plan_tasks
from core.router import route_task
from core.types import AgentExecutor


memory = Memory()


def run_engine(prompt: str, agent_executor: AgentExecutor) -> str:
    memory.add("user", prompt)

    tasks = plan_tasks(prompt)

    responses = []

    for task in tasks:
        domain = route_task(task)

        result = agent_executor(domain, prompt)

        responses.append(result)

    final_output = "\n\n".join(responses)

    final_output = review_output(final_output)

    memory.add("assistant", final_output)

    return final_output
