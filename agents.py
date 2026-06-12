from dataclasses import dataclass

from crewai import Agent


@dataclass
class GatewayAgents:
    router: Agent
    market: Agent
    technical: Agent
    writer: Agent


def create_router_agent(llm):
    return Agent(
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
    return Agent(
        role="Market Analyst",
        goal="Analyze market trends using real-time search data.",
        backstory="Expert in global markets and AI business strategy.",
        tools=search_tools,
        llm=llm,
        verbose=True
    )


def create_tech_agent(llm):
    return Agent(
        role="Technical Architect",
        goal="Design scalable system architectures.",
        backstory="Expert in distributed systems and AI engineering.",
        llm=llm,
        verbose=True
    )


def create_writer_agent(llm):
    return Agent(
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
