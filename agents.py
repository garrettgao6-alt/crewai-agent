import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from openai import OpenAI

if TYPE_CHECKING:
    from crewai import Agent


DEFAULT_AGENT_MODEL = os.getenv("OPENAI_COPILOT_MODEL", "gpt-4o-mini")


@dataclass
class GatewayAgents:
    router: "Agent"
    market: "Agent"
    technical: "Agent"
    writer: "Agent"


def _create_crewai_agent(**kwargs):
    from crewai import Agent

    return Agent(**kwargs)


def create_router_agent(llm):
    return _create_crewai_agent(
        role="AI Task Router",
        goal="Classify user requests into categories and return JSON.",
        backstory="""
You are an expert intent classifier.

You MUST respond in valid JSON format only:

{
  "category": "market" OR "technical" OR "writing",
  "confidence": a number between 0 and 1
}

No explanations.
No text outside JSON.
""",
        llm=llm,
        verbose=False
    )


def create_market_agent(llm, search_tools):
    return _create_crewai_agent(
        role="Market Analyst",
        goal="Analyze market trends using real-time search data.",
        backstory="Expert in global markets and AI business strategy.",
        tools=search_tools,
        llm=llm,
        verbose=True
    )


def create_tech_agent(llm):
    return _create_crewai_agent(
        role="Technical Architect",
        goal="Design scalable system architectures.",
        backstory="Expert in distributed systems and AI engineering.",
        llm=llm,
        verbose=True
    )


def create_writer_agent(llm):
    return _create_crewai_agent(
        role="Professional Writer",
        goal="Write clear executive-level documents.",
        backstory="Expert business writer.",
        llm=llm,
        verbose=True
    )


def create_agents(llm, search_tools):
    return GatewayAgents(
        router=create_router_agent(llm),
        market=create_market_agent(llm, search_tools),
        technical=create_tech_agent(llm),
        writer=create_writer_agent(llm)
    )


def _run_openai_agent(system_prompt: str, prompt: str) -> str:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        raise ValueError("Agent prompt is required.")

    client = OpenAI()
    response = client.responses.create(
        model=DEFAULT_AGENT_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": cleaned_prompt},
        ],
    )
    return response.output_text


def run_construction_agent(prompt: str) -> str:
    system_prompt = (
        "You are a senior construction consultant specializing in contracts, "
        "tenders, and risk analysis."
    )
    return _run_openai_agent(system_prompt, prompt)


def run_business_agent(prompt: str) -> str:
    system_prompt = (
        "You are a senior business strategist focused on growth, finance, "
        "and operations."
    )
    return _run_openai_agent(system_prompt, prompt)


def run_general_agent(prompt: str) -> str:
    system_prompt = "You are a helpful AI assistant."
    return _run_openai_agent(system_prompt, prompt)
