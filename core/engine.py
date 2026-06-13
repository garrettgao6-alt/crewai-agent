from agents import (
    run_business_agent,
    run_construction_agent,
    run_general_agent,
)
from core.critic import review_output
from core.memory import Memory
from core.planner import plan_tasks
from core.reasoning import build_reasoning_prompt, chunks_to_clauses
from core.report_generator import generate_report
from core.retriever import retrieve_multi
from core.router import route_task


memory = Memory()


def agent_executor(domain, prompt):
    if domain == "construction":
        return run_construction_agent(prompt)

    if domain == "business":
        return run_business_agent(prompt)

    return run_general_agent(prompt)


def run_engine(user_id, prompt, document_text=None):
    history = memory.get(user_id)
    tasks = plan_tasks(prompt)
    retrieved_chunks = retrieve_multi(user_id, prompt)
    clauses = chunks_to_clauses(retrieved_chunks)
    reasoning_prompt = build_reasoning_prompt(prompt, clauses)

    if document_text:
        reasoning_prompt = f"{reasoning_prompt}\n\nAdditional document text:\n{document_text}"

    if history:
        reasoning_prompt = f"{reasoning_prompt}\n\nConversation history:\n{history}"

    results = []

    for task in tasks:
        domain = route_task(task)
        result = agent_executor(domain, reasoning_prompt)
        result = review_output(result)

        results.append(
            {
                "task": task,
                "domain": domain,
                "result": result,
            }
        )

    final_output = generate_report(
        {
            "summary": "AI system execution report generated from planner, router, RAG, reasoning, agents, and critic.",
            "clauses": [clause["clause"] for clause in clauses],
            "analysis": "\n\n".join([result["result"] for result in results]),
            "risk": "AUTO",
            "recommendations": "AUTO",
        }
    )

    memory.add(user_id, "user", prompt)
    memory.add(user_id, "assistant", final_output)

    return final_output
