from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI


# ===== LLM =====
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7
)


# ===== Agents =====

market_agent = Agent(
    role="Market Analyst",
    goal="Analyze market trends and business opportunities",
    backstory="Expert in global markets and AI business analysis.",
    llm=llm,
    verbose=True
)

tech_agent = Agent(
    role="Technical Analyst",
    goal="Analyze technical feasibility and architecture",
    backstory="Expert in software architecture and AI systems.",
    llm=llm,
    verbose=True
)

writer_agent = Agent(
    role="Professional Writer",
    goal="Write clear and structured reports",
    backstory="Professional content writer.",
    llm=llm,
    verbose=True
)


# ===== Gateway Logic =====

def route_task(user_input: str):
    user_input_lower = user_input.lower()

    if "market" in user_input_lower:
        return market_agent
    elif "technical" in user_input_lower or "architecture" in user_input_lower:
        return tech_agent
    else:
        return writer_agent


def run_gateway(user_input: str):
    selected_agent = route_task(user_input)

    task = Task(
        description=user_input,
        expected_output="A detailed and professional response.",
        agent=selected_agent
    )

    crew = Crew(
        agents=[selected_agent],
        tasks=[task],
        verbose=True
    )

    result = crew.kickoff()
    return result


# ===== Entry Point =====

if __name__ == "__main__":
    print("\n=== AI Gateway ===")
    user_input = input("Enter your request: ")

    result = run_gateway(user_input)

    print("\n=== FINAL RESULT ===\n")
    print(result)
