from __future__ import annotations

from crewai import Agent, Crew, Task

from config import create_llm, load_environment


VERSION = "1.0"
EXECUTIVE_ERROR_MESSAGE = (
    "Executive agent team failed: unable to reach the LLM provider. "
    "Please try again later."
)


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


def run_executive_agent_team(review_type: str, documents_text: str) -> dict:
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

    contract_task = build_task(
        contract_agent,
        review_type,
        documents_text,
        "- contract obligations\n- payment terms\n- variation clauses\n- EOT\n- delay damages\n- dispute clauses",
    )
    tender_task = build_task(
        tender_agent,
        review_type,
        documents_text,
        "- scope gaps\n- tender risks\n- exclusions\n- commercial qualifications\n- clarification questions",
    )
    risk_task = build_task(
        risk_agent,
        review_type,
        documents_text,
        "- commercial risks\n- programme risks\n- safety risks\n- procurement risks\n- risk matrix",
    )
    ncc_task = build_task(
        ncc_agent,
        review_type,
        documents_text,
        "- NCC compliance\n- building class\n- fire safety\n- accessibility\n- energy efficiency\n- documentation risks",
    )
    finance_task = build_task(
        finance_agent,
        review_type,
        documents_text,
        "- cash flow\n- cost exposure\n- margin risk\n- contingency\n- financial implications",
    )
    bim_task = build_task(
        bim_agent,
        review_type,
        documents_text,
        "- BIM opportunities\n- digital twin\n- clash detection\n- quantity takeoff\n- site reporting automation",
    )
    coordinator_task = Task(
        description=f"""
Review Type: {review_type}

Create a final board-level executive report from the specialist agent outputs.
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
        context=[
            contract_task,
            tender_task,
            risk_task,
            ncc_task,
            finance_task,
            bim_task,
        ],
    )

    crew = Crew(
        agents=[
            contract_agent,
            tender_agent,
            risk_agent,
            ncc_agent,
            finance_agent,
            bim_agent,
            coordinator_agent,
        ],
        tasks=[
            contract_task,
            tender_task,
            risk_task,
            ncc_task,
            finance_task,
            bim_task,
            coordinator_task,
        ],
        verbose=True,
    )

    try:
        result = crew.kickoff()
    except Exception:
        return {
            "category": "executive",
            "confidence": 0.0,
            "result": EXECUTIVE_ERROR_MESSAGE,
            "version": VERSION,
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
    }
