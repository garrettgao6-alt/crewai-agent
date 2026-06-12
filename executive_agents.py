from __future__ import annotations

from crewai import Agent, Crew, Task

from config import create_llm, load_environment


VERSION = "1.0"
EXECUTIVE_ERROR_MESSAGE = (
    "Executive agent team failed: unable to reach the LLM provider. "
    "Please try again later."
)
FAST_EXECUTIVE_REVIEW = "Fast Executive Review"
FULL_BOARD_REVIEW = "Full Board Review"
DEEP_DUE_DILIGENCE = "Deep Due Diligence"
AGENT_MODES = [FAST_EXECUTIVE_REVIEW, FULL_BOARD_REVIEW, DEEP_DUE_DILIGENCE]

AGENT_MODE_ROLES = {
    FAST_EXECUTIVE_REVIEW: ["Executive Coordinator Agent"],
    FULL_BOARD_REVIEW: [
        "Contract Intelligence Agent",
        "Risk Intelligence Agent",
        "Finance Intelligence Agent",
        "Executive Coordinator Agent",
    ],
    DEEP_DUE_DILIGENCE: [
        "Contract Intelligence Agent",
        "Tender Intelligence Agent",
        "Risk Intelligence Agent",
        "NCC Compliance Agent",
        "Finance Intelligence Agent",
        "BIM Intelligence Agent",
        "Executive Coordinator Agent",
    ],
}


def build_agent(role: str, goal: str, backstory: str, llm) -> Agent:
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=llm,
        verbose=True,
    )


def build_task(agent: Agent, review_type: str, documents_text: str, focus: str) -> Task:
    return Task(
        description=f"""
Review Type: {review_type}

Project Documents:
{documents_text}

Analyze only the uploaded document content. Do not use web search.

Focus:
{focus}
""".strip(),
        expected_output="A concise executive intelligence report section with findings, risks, and recommendations.",
        agent=agent,
    )


def run_executive_agent_team(
    review_type: str,
    documents_text: str,
    agent_mode: str = DEEP_DUE_DILIGENCE,
) -> dict:
    load_environment()
    llm = create_llm()

    contract_agent = build_agent(
        role="Contract Intelligence Agent",
        goal="Identify contract obligations, payment terms, variation clauses, EOT exposure, delay damages, and dispute clauses.",
        backstory=(
            "You are a senior construction contract analyst who reviews project documents "
            "for obligations, claims exposure, and commercial contract risks."
        ),
        llm=llm,
    )
    tender_agent = build_agent(
        role="Tender Intelligence Agent",
        goal="Identify scope gaps, tender risks, exclusions, commercial qualifications, and clarification questions.",
        backstory=(
            "You are an experienced tender reviewer who finds scope gaps, ambiguous requirements, "
            "pricing risks, and clarification items before submission or acceptance."
        ),
        llm=llm,
    )
    risk_agent = build_agent(
        role="Risk Intelligence Agent",
        goal="Identify commercial, programme, safety, procurement, and priority risk matrix items.",
        backstory=(
            "You are a project risk advisor who consolidates operational, delivery, safety, "
            "procurement, and commercial risks into clear action priorities."
        ),
        llm=llm,
    )
    ncc_agent = build_agent(
        role="NCC Compliance Agent",
        goal="Identify NCC compliance, building class, fire safety, accessibility, energy efficiency, and documentation risks.",
        backstory=(
            "You are a compliance-focused construction advisor with practical knowledge of "
            "Australian building compliance review workflows."
        ),
        llm=llm,
    )
    finance_agent = build_agent(
        role="Finance Intelligence Agent",
        goal="Assess cash flow, cost exposure, margin risk, contingency, and financial implications.",
        backstory=(
            "You are a construction finance and commercial analyst who reviews project documents "
            "for margin, cash flow, cost exposure, and contingency risks."
        ),
        llm=llm,
    )
    bim_agent = build_agent(
        role="BIM Intelligence Agent",
        goal="Identify BIM, digital twin, clash detection, quantity takeoff, and site reporting automation opportunities.",
        backstory=(
            "You are a digital construction strategist who identifies practical BIM, automation, "
            "digital twin, quantity, reporting, and coordination opportunities."
        ),
        llm=llm,
    )
    coordinator_agent = build_agent(
        role="Executive Coordinator Agent",
        goal="Combine all agent outputs, remove duplication, create a board-level report, and provide final recommendations.",
        backstory=(
            "You are an executive advisor who synthesizes specialist findings into a clear, "
            "board-level report with priorities, risk ranking, and practical next actions."
        ),
        llm=llm,
    )

    agent_mode = agent_mode if agent_mode in AGENT_MODE_ROLES else DEEP_DUE_DILIGENCE
    selected_roles = AGENT_MODE_ROLES[agent_mode]
    specialist_definitions = [
        (
            contract_agent,
            "Contract Intelligence Agent",
            "- contract obligations\n- payment terms\n- variation clauses\n- EOT\n- delay damages\n- dispute clauses",
        ),
        (
            tender_agent,
            "Tender Intelligence Agent",
            "- scope gaps\n- tender risks\n- exclusions\n- commercial qualifications\n- clarification questions",
        ),
        (
            risk_agent,
            "Risk Intelligence Agent",
            "- commercial risks\n- programme risks\n- safety risks\n- procurement risks\n- risk matrix",
        ),
        (
            ncc_agent,
            "NCC Compliance Agent",
            "- NCC compliance\n- building class\n- fire safety\n- accessibility\n- energy efficiency\n- documentation risks",
        ),
        (
            finance_agent,
            "Finance Intelligence Agent",
            "- cash flow\n- cost exposure\n- margin risk\n- contingency\n- financial implications",
        ),
        (
            bim_agent,
            "BIM Intelligence Agent",
            "- BIM opportunities\n- digital twin\n- clash detection\n- quantity takeoff\n- site reporting automation",
        ),
    ]
    specialist_tasks = [
        build_task(agent, review_type, documents_text, focus)
        for agent, role, focus in specialist_definitions
        if role in selected_roles
    ]

    coordinator_context = specialist_tasks
    coordinator_source = "the specialist agent outputs"
    if not specialist_tasks:
        coordinator_context = []
        coordinator_source = "the uploaded project documents"

    coordinator_task = Task(
        description=f"""
Review Type: {review_type}
Agent Mode: {agent_mode}

Project Documents:
{documents_text}

Create a final board-level executive report from {coordinator_source}.
Remove duplication, resolve conflicts, prioritize risks, and provide final recommendations.

Required structure:
1. Executive Summary
2. Key Findings by Domain
3. Cross-Document and Cross-Discipline Issues
4. Commercial Risks
5. Contractual Risks
6. Compliance / NCC Risks
7. Financial Implications
8. BIM / Digital Opportunities
9. Priority Matrix
10. Final Recommendations
""".strip(),
        expected_output="A complete board-level executive intelligence report.",
        agent=coordinator_agent,
        context=coordinator_context,
    )
    agent_lookup = {
        "Contract Intelligence Agent": contract_agent,
        "Tender Intelligence Agent": tender_agent,
        "Risk Intelligence Agent": risk_agent,
        "NCC Compliance Agent": ncc_agent,
        "Finance Intelligence Agent": finance_agent,
        "BIM Intelligence Agent": bim_agent,
        "Executive Coordinator Agent": coordinator_agent,
    }
    selected_agents = [agent_lookup[role] for role in selected_roles]
    selected_tasks = [*specialist_tasks, coordinator_task]
    crew = Crew(agents=selected_agents, tasks=selected_tasks, verbose=True)

    try:
        result = crew.kickoff()
    except Exception:
        return {
            "category": "executive",
            "confidence": 0.0,
            "result": EXECUTIVE_ERROR_MESSAGE,
            "version": VERSION,
            "agent_mode": agent_mode,
        }

    try:
        output = result.raw
    except AttributeError:
        output = str(result)

    return {
        "category": "executive",
        "confidence": 0.95,
        "result": output,
        "version": VERSION,
        "agent_mode": agent_mode,
    }
