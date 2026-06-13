from agents import (
    run_business_agent,
    run_construction_agent,
    run_general_agent,
)
from core.engine import run_engine


def agent_executor(domain, prompt):
    if domain == "construction":
        return run_construction_agent(prompt)

    if domain == "business":
        return run_business_agent(prompt)

    return run_general_agent(prompt)


def run_copilot(prompt: str) -> str:
    return run_engine(prompt, agent_executor)
