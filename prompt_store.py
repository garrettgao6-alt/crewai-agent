from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("prompts.db")


DEFAULT_PROMPTS = [
    {
        "category": "Business",
        "name": "Market Research",
        "content": """Conduct a professional market research report.

Industry:
Location:
Target Customers:
Product / Service:

Provide:

1. Market overview
2. Market size and demand drivers
3. Customer segments
4. Competitor landscape
5. Pricing and positioning
6. Growth opportunities
7. Risks and barriers
8. Strategic recommendations""",
    },
    {
        "category": "Business",
        "name": "Product Roadmap",
        "content": """Create a 90-day product roadmap.

Product:
Target Users:
Business Goal:
Current Stage:

Provide:

1. Product vision
2. Key milestones
3. Feature priorities
4. Timeline by phase
5. Resource requirements
6. Risks and dependencies
7. Success metrics
8. Recommended next actions""",
    },
    {
        "category": "Business",
        "name": "Supply Chain",
        "content": """Analyze the supply chain strategy.

Business:
Industry:
Key Suppliers:
Main Products / Materials:

Provide:

1. Procurement risks
2. Supplier dependency risks
3. Logistics and delivery risks
4. Cost reduction opportunities
5. Inventory strategy
6. Alternative supplier options
7. Process improvement plan
8. Recommendations""",
    },
    {
        "category": "Business",
        "name": "Business Analysis",
        "content": """Perform a business analysis.

Business:
Industry:
Current Challenge:

Provide:

1. SWOT analysis
2. Revenue opportunities
3. Operational weaknesses
4. Cost improvement areas
5. Customer and market risks
6. Strategic options
7. Recommended action plan""",
    },
    {
        "category": "Business",
        "name": "Accounting",
        "content": """Review the following accounting and financial scenario.

Business Type:
Revenue:
Expenses:
Main Financial Concern:

Provide:

1. Financial risk assessment
2. Cost control recommendations
3. Cash flow analysis
4. Budget improvement suggestions
5. Profitability review
6. Key financial KPIs
7. Practical next steps""",
    },
    {
        "category": "Business",
        "name": "Customer Service",
        "content": """Create a customer service improvement plan.

Business:
Customer Type:
Current Problems:

Provide:

1. Key pain points
2. Response process improvements
3. Automation opportunities
4. AI chatbot opportunities
5. Customer satisfaction KPIs
6. Staff training recommendations
7. Implementation roadmap""",
    },
    {
        "category": "Business",
        "name": "Competitor Analysis",
        "content": """Perform a competitor analysis.

Company:
Industry:
Location:
Main Competitors:

Provide:

1. Competitor profiles
2. Strengths and weaknesses
3. Pricing comparison
4. Market positioning
5. Differentiation opportunities
6. Threats
7. Strategic recommendations""",
    },
    {
        "category": "Business",
        "name": "Trend Analysis",
        "content": """Perform an industry trend analysis.

Industry:
Region:
Time Horizon:

Provide:

1. Current market trends
2. Emerging technologies
3. Customer behavior changes
4. Regulatory or economic drivers
5. Risks
6. Opportunities
7. Strategic recommendations""",
    },
    {
        "category": "Business",
        "name": "Sales Analysis",
        "content": """Analyze sales performance.

Business:
Product / Service:
Period:
Sales Data / Observations:

Provide:

1. Revenue trend analysis
2. Customer segment analysis
3. Underperforming areas
4. Growth opportunities
5. Sales funnel improvements
6. KPI recommendations
7. Action plan""",
    },
    {
        "category": "Construction",
        "name": "Project Plan",
        "content": """Create a construction project execution plan.

Project:
Location:
Building Type:
Budget:
Duration:
Key Constraints:

Provide:

1. Project phases
2. Scope breakdown
3. Milestones
4. Resource allocation
5. Site management approach
6. Risk management plan
7. Communication plan
8. Timeline summary""",
    },
    {
        "category": "Construction",
        "name": "Building Codes (NCC & Housing Provisions)",
        "content": """Review this construction scenario against Australian NCC and Housing Provisions.

Project:
Location:
Building Class:
Scope of Works:

Provide:

1. Relevant NCC considerations
2. Housing Provision considerations if applicable
3. Compliance risks
4. Documentation required
5. Design or construction issues to check
6. Recommended actions
7. Questions to confirm with certifier / building surveyor""",
    },
    {
        "category": "Construction",
        "name": "NCC 2025 Compliance Review",
        "content": """Review this project for potential NCC 2025 compliance issues.

Project:
Location:
Building Type:
Design Stage:
Scope:

Provide:

1. Likely NCC 2025 considerations
2. Energy efficiency considerations
3. Livable housing / accessibility considerations if applicable
4. Waterproofing, fire, structure, ventilation, and safety items to check
5. Compliance documentation checklist
6. Risk areas
7. Recommended next steps""",
    },
    {
        "category": "Construction",
        "name": "Supervision Plan",
        "content": """Create a construction site supervision plan.

Project:
Location:
Trade / Scope:
Stage of Works:

Provide:

1. Daily supervision checklist
2. Quality control checkpoints
3. Safety responsibilities
4. Communication and reporting process
5. Inspection hold points
6. Escalation process
7. Supervisor daily report format""",
    },
    {
        "category": "Construction",
        "name": "Site Progress Report",
        "content": """Generate a professional construction site progress report.

Project:
Date / Week:
Completed Works:
Current Activities:
Delays / Issues:
Upcoming Works:

Provide:

1. Executive summary
2. Completed works
3. Work in progress
4. Issues and delays
5. Safety observations
6. Quality observations
7. Upcoming activities
8. Action items""",
    },
    {
        "category": "Construction",
        "name": "Risk Assessment",
        "content": """Perform a construction risk assessment.

Project:
Location:
Scope:
Stage:

Identify:

1. Safety risks
2. Cost risks
3. Schedule risks
4. Quality risks
5. Environmental risks
6. Legal / compliance risks
7. Mitigation measures
8. Responsible parties""",
    },
    {
        "category": "Construction",
        "name": "Cost Estimate",
        "content": """Prepare a preliminary construction cost estimate.

Project:
Building Type:
Floor Area:
Location:
Scope:

Provide:

1. Major cost categories
2. Cost assumptions
3. Labour, materials, plant and subcontractor considerations
4. Contingency allowance
5. Risk allowances
6. Exclusions
7. Budget summary""",
    },
    {
        "category": "Construction",
        "name": "Safety Inspection",
        "content": """Generate a construction safety inspection report.

Project:
Site:
Date:
Observations:

Provide:

1. Hazards identified
2. Risk rating
3. Immediate corrective actions
4. Responsible persons
5. Due dates
6. Follow-up requirements
7. Safety summary""",
    },
    {
        "category": "Construction",
        "name": "Toolbox Meeting",
        "content": """Generate a toolbox meeting agenda and record.

Project:
Date:
Topic:
Attendees:

Provide:

1. Safety topic overview
2. Site-specific risks
3. Control measures
4. Worker responsibilities
5. Questions for discussion
6. Action items
7. Attendance record section""",
    },
    {
        "category": "Construction",
        "name": "Construction Laws Analysis",
        "content": """Analyze applicable construction laws and regulatory risks.

Project:
Location:
Contract Type:
Issue:

Provide:

1. Relevant legal and regulatory considerations
2. Contractual obligations
3. Compliance risks
4. Documentation required
5. Possible consequences
6. Recommended practical actions
7. Items requiring legal advice""",
    },
    {
        "category": "Construction",
        "name": "Tender Review",
        "content": """Review the following construction tender submission.

Project:
Client:
Contract Type:
Tender Scope:

Provide:

1. Commercial risks
2. Technical risks
3. Scope gaps
4. Ambiguous clauses
5. Missing documentation
6. Pricing risks
7. Clarification questions
8. Recommendation: proceed / proceed with conditions / do not proceed""",
    },
    {
        "category": "Construction",
        "name": "RFI Generator",
        "content": """Create a professional Request for Information.

Project:
Drawing / Specification Reference:
Issue:
Impact:

Provide:

1. RFI title
2. Background
3. Specific question
4. Reason for request
5. Potential cost / time impact
6. Required response date
7. Professional wording""",
    },
    {
        "category": "Construction",
        "name": "Variation Claim",
        "content": """Prepare a construction variation claim.

Project:
Contract:
Variation Description:
Cause:
Cost Impact:
Time Impact:

Provide:

1. Variation summary
2. Contract basis
3. Scope change explanation
4. Cost breakdown
5. Time impact
6. Supporting evidence checklist
7. Formal claim wording""",
    },
    {
        "category": "Construction",
        "name": "Subcontractor Evaluation",
        "content": """Evaluate a subcontractor.

Subcontractor:
Trade:
Project:
Performance Observations:

Provide:

1. Capability assessment
2. Quality performance
3. Safety performance
4. Programme performance
5. Communication performance
6. Commercial risks
7. Recommendation
8. Scorecard format""",
    },
    {
        "category": "Construction",
        "name": "Contract Analysis",
        "content": """Analyze this construction contract.

Project:
Contract Type:
Clause / Issue:
Concern:

Provide:

1. Key obligations
2. Risk clauses
3. Payment terms
4. Variation process
5. Delay and extension of time clauses
6. Dispute resolution process
7. Practical recommendations
8. Items requiring legal review""",
    },
    {
        "category": "Construction",
        "name": "BIM + AI",
        "content": """Analyze BIM and AI opportunities for this construction project.

Project:
Stage:
Current Tools:
Main Problems:

Provide:

1. BIM workflow improvements
2. AI automation opportunities
3. Clash detection benefits
4. Quantity takeoff opportunities
5. Programme and cost control opportunities
6. Site reporting automation
7. Implementation roadmap
8. Risks and limitations""",
    },
    {
        "category": "Construction",
        "name": "Digital Twin Strategy",
        "content": """Create a digital twin strategy for a construction or asset project.

Project:
Asset Type:
Project Stage:
Available Data:

Provide:

1. Digital twin objectives
2. Required data sources
3. BIM / IoT / sensor integration
4. Operations and maintenance use cases
5. Cost and performance benefits
6. Implementation roadmap
7. Risks and governance requirements""",
    },
    {
        "category": "Construction",
        "name": "Prefabrication / Modular Construction",
        "content": """Assess prefabrication or modular construction opportunities.

Project:
Building Type:
Location:
Scope:

Provide:

1. Suitable prefabrication elements
2. Benefits
3. Cost and programme impacts
4. Design coordination requirements
5. Logistics considerations
6. Risks
7. Recommendation""",
    },
    {
        "category": "Construction",
        "name": "Construction Productivity Improvement",
        "content": """Create a construction productivity improvement plan.

Project:
Trade / Scope:
Current Bottlenecks:

Provide:

1. Productivity issues
2. Workflow improvements
3. Labour and resource optimisation
4. Digital tool opportunities
5. AI automation opportunities
6. KPIs to track
7. Implementation plan""",
    },
    {
        "category": "Construction",
        "name": "Defect / Quality Inspection",
        "content": """Generate a defect and quality inspection report.

Project:
Area:
Inspection Date:
Observed Defects:

Provide:

1. Defect list
2. Severity rating
3. Likely causes
4. Required rectification
5. Responsible party
6. Due date
7. Reinspection checklist""",
    },
    {
        "category": "Construction",
        "name": "Procurement Risk Review",
        "content": """Review procurement risks for a construction project.

Project:
Key Materials:
Suppliers:
Programme Requirements:

Provide:

1. Long-lead items
2. Supplier risks
3. Price escalation risks
4. Logistics risks
5. Alternative procurement options
6. Mitigation strategy
7. Procurement action plan""",
    },
]


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_prompt_store(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, name)
            )
            """
        )
        prompt_count = connection.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
        if prompt_count == 0:
            seed_default_prompts(connection)


def seed_default_prompts(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT INTO prompts (category, name, content, version)
        VALUES (:category, :name, :content, 1)
        """,
        DEFAULT_PROMPTS,
    )


def list_categories(db_path: Path = DB_PATH) -> list[str]:
    initialize_prompt_store(db_path)
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT DISTINCT category FROM prompts ORDER BY category"
        ).fetchall()
    return [row["category"] for row in rows]


def list_prompts(category: str, db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    initialize_prompt_store(db_path)
    with get_connection(db_path) as connection:
        return connection.execute(
            """
            SELECT id, category, name, content, version, created_at, updated_at
            FROM prompts
            WHERE category = ?
            ORDER BY name
            """,
            (category,),
        ).fetchall()


def get_prompt(prompt_id: int, db_path: Path = DB_PATH) -> sqlite3.Row | None:
    initialize_prompt_store(db_path)
    with get_connection(db_path) as connection:
        return connection.execute(
            """
            SELECT id, category, name, content, version, created_at, updated_at
            FROM prompts
            WHERE id = ?
            """,
            (prompt_id,),
        ).fetchone()


if __name__ == "__main__":
    initialize_prompt_store()
    print(f"Prompt store initialized at {DB_PATH}")
