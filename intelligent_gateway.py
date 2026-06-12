import json
import os
from pathlib import Path
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv(Path(__file__).resolve().parent / ".env")
else:
    print("Warning: python-dotenv is not installed; .env auto-load skipped.")


# =====================================================
# LLM CONFIG
# =====================================================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


# =====================================================
# ROUTER AGENT (JSON OUTPUT)
# =====================================================

router_agent = Agent(
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


# =====================================================
# SPECIALIST AGENTS
# =====================================================

def build_search_tools():
    if not os.getenv("TAVILY_API_KEY"):
        print("Warning: TAVILY_API_KEY is not set; Tavily search disabled.")
        return []

    try:
        from crewai_tools import TavilySearchTool
    except ImportError:
        print("Warning: crewai_tools.TavilySearchTool is unavailable; Tavily search disabled.")
        return []

    try:
        return [TavilySearchTool()]
    except Exception as exc:
        print(f"Warning: TavilySearchTool initialization failed; Tavily search disabled. Details: {exc}")
        return []


search_tools = build_search_tools()

market_agent = Agent(
    role="Market Analyst",
    goal="Analyze market trends using real-time search data.",
    backstory="Expert in global markets and AI business strategy.",
    tools=search_tools,
    llm=llm,
    verbose=True
)

tech_agent = Agent(
    role="Technical Architect",
    goal="Design scalable system architectures.",
    backstory="Expert in distributed systems and AI engineering.",
    llm=llm,
    verbose=True
)

writer_agent = Agent(
    role="Professional Writer",
    goal="Write clear executive-level documents.",
    backstory="Expert business writer.",
    llm=llm,
    verbose=True
)


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

    result = crew.kickoff()

    # SAFE extraction
    try:
        raw_output = result.raw
    except AttributeError:
        raw_output = str(result)

    raw_output = raw_output.strip()

    print("\nRouter Raw Output:")
    print(raw_output)

    # SAFE JSON parsing
    try:
        parsed = json.loads(raw_output)
        category = parsed.get("category", "writing").lower()
        confidence = parsed.get("confidence", 0.5)
    except Exception:
        print("⚠ JSON parsing failed. Using fallback.")
        category = "writing"
        confidence = 0.5

    # Extra safety
    if category not in ["market", "technical", "writing"]:
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

    print("\n--- Routing Decision ---\n")

    category, confidence = classify_request(user_input)

    print(f"\nFinal Classification: {category}")
    print(f"Confidence: {confidence}\n")

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

    result = crew.kickoff()

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
