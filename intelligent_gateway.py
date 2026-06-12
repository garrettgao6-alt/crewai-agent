import json
import logging
import os
from crewai import Task, Crew

from agents import create_agents
from config import build_search_tools, create_llm, load_environment


logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(levelname)s:%(name)s:%(message)s",
    )


# =====================================================
# GATEWAY SETUP
# =====================================================

configure_logging()
load_environment()
llm = create_llm()
search_tools = build_search_tools()
gateway_agents = create_agents(llm, search_tools)
router_agent = gateway_agents.router
market_agent = gateway_agents.market
tech_agent = gateway_agents.technical
writer_agent = gateway_agents.writer


# =====================================================
# CLASSIFICATION FUNCTION
# =====================================================

def classify_request(user_input: str):

    classification_task = Task(
        description=f"""
Classify this request:

{user_input}

Respond ONLY in valid JSON.
""",
        expected_output="Valid JSON with category and confidence.",
        agent=router_agent
    )

    crew = Crew(
        agents=[router_agent],
        tasks=[classification_task],
        verbose=False
    )

    try:
        result = crew.kickoff()
    except Exception:
        logger.exception("Router crew kickoff failed; falling back to writing.")
        return "writing", 0.0

    # SAFE extraction
    try:
        raw_output = result.raw
    except AttributeError:
        raw_output = str(result)

    raw_output = raw_output.strip()

    logger.debug("Router raw output: %s", raw_output)

    # SAFE JSON parsing
    try:
        parsed = json.loads(raw_output)
        category = parsed.get("category", "writing").lower()
        confidence = parsed.get("confidence", 0.5)
    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning("JSON parsing failed. Using writing fallback.")
        category = "writing"
        confidence = 0.5

    # Extra safety
    if category not in ["market", "technical", "writing"]:
        logger.warning("Unknown router category '%s'. Using writing fallback.", category)
        category = "writing"

    return category, confidence


# =====================================================
# AGENT SELECTOR
# =====================================================

def select_agent(category: str):
    agent_map = {
        "market": market_agent,
        "technical": tech_agent,
        "writing": writer_agent
    }
    return agent_map.get(category, writer_agent)


# =====================================================
# GATEWAY EXECUTION
# =====================================================

def run_gateway(user_input: str):

    logger.info("Routing request.")

    category, confidence = classify_request(user_input)

    logger.info("Final classification: %s", category)
    logger.info("Confidence: %s", confidence)

    selected_agent = select_agent(category)

    main_task = Task(
        description=user_input,
        expected_output="A professional detailed response.",
        agent=selected_agent
    )

    crew = Crew(
        agents=[selected_agent],
        tasks=[main_task],
        verbose=True
    )

    try:
        result = crew.kickoff()
    except Exception:
        logger.exception("Specialist crew kickoff failed.")
        return "Gateway execution failed: unable to reach the LLM provider. Please try again later."

    try:
        return result.raw
    except AttributeError:
        return str(result)


# =====================================================
# ENTRY POINT
# =====================================================

if __name__ == "__main__":

    print("\n=== Enterprise JSON AI Gateway ===")

    user_input = input("Enter your request: ")

    final_result = run_gateway(user_input)

    print("\n=== FINAL RESULT ===\n")
    print(final_result)
