from agents import (
    run_business_agent,
    run_construction_agent,
    run_general_agent,
)
from router import detect_intent


def run_copilot(prompt: str) -> str:
    intent = detect_intent(prompt)

    if intent == "construction":
        return run_construction_agent(prompt)

    if intent == "business":
        return run_business_agent(prompt)

    return run_general_agent(prompt)
