from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7
)

# Agent 1
researcher = Agent(
    role="Market بمن Research Analyst",
    goal="Research AI automation market trends in 2026",
    backstory="Expert market analyst specializing in AI industry trends.",
    llm=llm,
    verbose=True
)

# Agent 2
writer = Agent(
    role="Business Report Writer",
    goal="Write executive summaries based on research findings",
    backstory="Professional business writer.",
    llm=llm,
    verbose=True
)

# Task 1
task1 = Task(
    description="Analyze key trends, opportunities, and risks in AI automation for 2026.",
    expected_output="A detailed analysis of AI automation trends, opportunities, and risks in 2026.",
    agent=researcher
)

# Task 2
task2 = Task(
    description="Write a 200-word executive summary based on the research findings.",
    expected_output="A concise 200-word executive summary.",
    agent=writer
)

# Crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    verbose=True
)

# Run
result = crew.kickoff()

print("\n===== FINAL RESULT =====\n")
print(result)
