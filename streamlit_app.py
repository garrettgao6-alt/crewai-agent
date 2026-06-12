import json
from io import BytesIO
import time

import requests
import streamlit as st

import prompt_store


API_URL = "http://127.0.0.1:8000/analyze"
REQUEST_TIMEOUT_SECONDS = 60
VERSION = "1.0"
HISTORY_LIMIT = 10
DOCUMENT_TEXT_LIMIT = 12000
DOCUMENT_ANALYSIS_TYPES = [
    "Contract Review",
    "Tender Review",
    "Risk Assessment",
    "Meeting Minutes",
    "Progress Report",
    "Safety Inspection",
    "Business Analysis",
]
DOCUMENT_REPORT_STRUCTURES = {
    "Contract Review": [
        "Executive summary",
        "Key contract obligations",
        "Risk clauses and exposure areas",
        "Payment, variation, delay, and EOT considerations",
        "Ambiguous or unfavorable terms",
        "Required clarifications or missing documents",
        "Practical negotiation recommendations",
        "Items requiring legal review",
    ],
    "Tender Review": [
        "Tender summary",
        "Commercial risks",
        "Technical risks",
        "Scope gaps and exclusions",
        "Programme and delivery risks",
        "Pricing assumptions and cost exposure",
        "Clarification questions",
        "Recommendation: proceed, proceed with conditions, or do not proceed",
    ],
    "Risk Assessment": [
        "Executive risk summary",
        "Safety risks",
        "Cost risks",
        "Schedule risks",
        "Quality risks",
        "Legal, compliance, and environmental risks",
        "Mitigation measures and responsible parties",
        "Priority risk matrix",
    ],
    "Meeting Minutes": [
        "Meeting summary",
        "Attendees and roles if available",
        "Key discussion points",
        "Decisions made",
        "Action items with owners and due dates",
        "Open issues",
        "Risks or blockers raised",
        "Next meeting or follow-up requirements",
    ],
    "Progress Report": [
        "Executive progress summary",
        "Completed works",
        "Current activities",
        "Delays, blockers, and causes",
        "Safety and quality observations",
        "Upcoming works",
        "Required decisions or support",
        "Action items and priority status",
    ],
    "Safety Inspection": [
        "Safety inspection summary",
        "Hazards identified",
        "Risk ratings",
        "Immediate corrective actions",
        "Responsible persons",
        "Due dates and follow-up requirements",
        "Recurring safety issues",
        "Overall safety recommendations",
    ],
    "Business Analysis": [
        "Executive business summary",
        "SWOT analysis",
        "Revenue and growth opportunities",
        "Operational weaknesses",
        "Cost improvement areas",
        "Customer, market, and competitive risks",
        "Strategic options",
        "Recommended action plan and priority matrix",
    ],
}

INDUSTRY_OPTIONS = [
    "Construction",
    "Real Estate",
    "SaaS",
    "E-commerce",
    "Retail",
    "Manufacturing",
    "Finance",
    "Healthcare",
    "Education",
    "Hospitality",
    "Logistics",
    "Professional Services",
    "Other",
]
BUSINESS_STAGE_OPTIONS = [
    "Idea Stage",
    "Startup",
    "Growth",
    "Mature Business",
    "Expansion",
    "Turnaround",
]
STATE_OPTIONS = ["VIC", "NSW", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
BUILDING_TYPE_OPTIONS = [
    "Residential",
    "Commercial",
    "Industrial",
    "Mixed-use",
    "Infrastructure",
    "Retail",
    "Education",
    "Healthcare",
    "Fit-out",
    "Renovation",
    "Extension",
    "Civil Works",
]
BUILDING_CLASS_OPTIONS = [
    "Class 1a",
    "Class 1b",
    "Class 2",
    "Class 3",
    "Class 5",
    "Class 6",
    "Class 7a",
    "Class 7b",
    "Class 8",
    "Class 9a",
    "Class 9b",
    "Class 9c",
    "Class 10a",
    "Class 10b",
    "Class 10c",
]
CONTRACT_TYPE_OPTIONS = [
    "AS4000",
    "AS4902",
    "AS2124",
    "HIA",
    "MBA",
    "Lump Sum",
    "D&C",
    "GMP",
    "Cost Plus",
    "Construction Management",
    "Bespoke Contract",
]
RISK_LEVEL_OPTIONS = ["Low", "Medium", "High", "Critical"]
STAGE_OF_WORKS_OPTIONS = [
    "Site Establishment",
    "Demolition",
    "Excavation",
    "Footings",
    "Slab",
    "Framing",
    "Lock-up",
    "Rough-in",
    "Fit-off",
    "Waterproofing",
    "Cladding",
    "Roofing",
    "Finishes",
    "Handover",
]


def field(name: str, key: str, field_type: str = "text_input", options: list[str] | None = None) -> dict:
    return {"name": name, "key": key, "type": field_type, "options": options or []}


FORM_LIBRARY = {
    "Business": [
        {
            "category": "Business",
            "name": "Market Research",
            "fields": [
                field("Industry", "industry", "selectbox", INDUSTRY_OPTIONS),
                field("Region / Country", "region_country"),
                field("Target Customers", "target_customers"),
                field("Product / Service", "product_service"),
                field("Market Segment", "market_segment"),
                field("Business Stage", "business_stage", "selectbox", BUSINESS_STAGE_OPTIONS),
                field(
                    "Research Focus",
                    "research_focus",
                    "multiselect",
                    [
                        "Market Size",
                        "Customer Demand",
                        "Competitors",
                        "Pricing",
                        "Regulations",
                        "Technology Trends",
                        "Risks",
                        "Opportunities",
                    ],
                ),
            ],
            "template": """Conduct a professional market research report.

Industry: {industry}
Location: {region_country}
Target Customers: {target_customers}
Product / Service: {product_service}
Market Segment: {market_segment}
Business Stage: {business_stage}
Research Focus: {research_focus}

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
            "fields": [
                field("Product", "product"),
                field("Target Users", "target_users"),
                field("Business Goal", "business_goal"),
                field("Current Stage", "current_stage", "selectbox", ["Idea", "MVP", "Beta", "Launched", "Growth", "Scaling"]),
                field("Timeline", "timeline", "selectbox", ["30 Days", "60 Days", "90 Days", "6 Months", "12 Months"]),
                field(
                    "Priority Focus",
                    "priority_focus",
                    "multiselect",
                    ["Features", "UX", "Revenue", "Automation", "Integrations", "AI Features", "Compliance", "Customer Retention"],
                ),
            ],
            "template": """Create a {timeline} product roadmap.

Product: {product}
Target Users: {target_users}
Business Goal: {business_goal}
Current Stage: {current_stage}
Priority Focus: {priority_focus}

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
            "fields": [
                field("Business", "business"),
                field("Industry", "industry", "selectbox", INDUSTRY_OPTIONS),
                field("Key Suppliers", "key_suppliers", "text_area"),
                field("Main Products / Materials", "main_products_materials", "text_area"),
                field("Supply Chain Risk Level", "supply_chain_risk_level", "selectbox", RISK_LEVEL_OPTIONS),
                field(
                    "Procurement Focus",
                    "procurement_focus",
                    "multiselect",
                    [
                        "Cost Reduction",
                        "Supplier Diversification",
                        "Lead Time Reduction",
                        "Inventory Control",
                        "Quality Control",
                        "Sustainability",
                        "Local Sourcing",
                        "Risk Mitigation",
                    ],
                ),
            ],
            "template": """Analyze the supply chain strategy.

Business: {business}
Industry: {industry}
Key Suppliers: {key_suppliers}
Main Products / Materials: {main_products_materials}
Supply Chain Risk Level: {supply_chain_risk_level}
Procurement Focus: {procurement_focus}

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
            "fields": [
                field("Business", "business"),
                field("Industry", "industry", "selectbox", INDUSTRY_OPTIONS),
                field("Current Challenge", "current_challenge", "text_area"),
                field("Business Stage", "business_stage", "selectbox", BUSINESS_STAGE_OPTIONS),
                field(
                    "Analysis Focus",
                    "analysis_focus",
                    "multiselect",
                    [
                        "SWOT",
                        "Revenue Growth",
                        "Cost Reduction",
                        "Operations",
                        "Marketing",
                        "Customer Experience",
                        "Staffing",
                        "Risk Management",
                        "Technology Adoption",
                    ],
                ),
            ],
            "template": """Perform a business analysis.

Business: {business}
Industry: {industry}
Current Challenge: {current_challenge}
Business Stage: {business_stage}
Analysis Focus: {analysis_focus}

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
            "fields": [
                field("Business Type", "business_type"),
                field(
                    "Revenue Range",
                    "revenue_range",
                    "selectbox",
                    ["Pre-revenue", "Under $100k", "$100k-$500k", "$500k-$1m", "$1m-$5m", "$5m+"],
                ),
                field("Expense Category", "expense_category"),
                field("Main Financial Concern", "main_financial_concern", "text_area"),
                field(
                    "Accounting Focus",
                    "accounting_focus",
                    "multiselect",
                    ["Cash Flow", "Budgeting", "Profitability", "Cost Control", "Tax Planning", "Payroll", "Reporting", "Forecasting"],
                ),
            ],
            "template": """Review the following accounting and financial scenario.

Business Type: {business_type}
Revenue: {revenue_range}
Expenses: {expense_category}
Main Financial Concern: {main_financial_concern}
Accounting Focus: {accounting_focus}

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
            "fields": [
                field("Business", "business"),
                field("Customer Type", "customer_type"),
                field("Current Problems", "current_problems", "text_area"),
                field(
                    "Service Channel",
                    "service_channel",
                    "multiselect",
                    ["Email", "Phone", "Live Chat", "Social Media", "Website Form", "In-person", "AI Chatbot", "CRM"],
                ),
                field(
                    "Improvement Focus",
                    "improvement_focus",
                    "multiselect",
                    [
                        "Response Time",
                        "Customer Satisfaction",
                        "Automation",
                        "Escalation Process",
                        "Staff Training",
                        "Knowledge Base",
                        "Complaint Handling",
                        "Retention",
                    ],
                ),
            ],
            "template": """Create a customer service improvement plan.

Business: {business}
Customer Type: {customer_type}
Current Problems: {current_problems}
Service Channel: {service_channel}
Improvement Focus: {improvement_focus}

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
            "fields": [
                field("Company", "company"),
                field("Industry", "industry", "selectbox", INDUSTRY_OPTIONS),
                field("Location", "location"),
                field("Main Competitors", "main_competitors", "text_area"),
                field(
                    "Comparison Focus",
                    "comparison_focus",
                    "multiselect",
                    ["Pricing", "Product Features", "Service Quality", "Branding", "Marketing", "Customer Reviews", "Technology", "Market Share"],
                ),
            ],
            "template": """Perform a competitor analysis.

Company: {company}
Industry: {industry}
Location: {location}
Main Competitors: {main_competitors}
Comparison Focus: {comparison_focus}

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
            "fields": [
                field("Industry", "industry", "selectbox", INDUSTRY_OPTIONS),
                field("Region", "region"),
                field("Time Horizon", "time_horizon", "selectbox", ["Next 3 Months", "Next 6 Months", "Next 12 Months", "2-3 Years", "5 Years"]),
                field(
                    "Trend Focus",
                    "trend_focus",
                    "multiselect",
                    [
                        "AI",
                        "Automation",
                        "Regulation",
                        "Sustainability",
                        "Customer Behavior",
                        "Economic Conditions",
                        "Technology Adoption",
                        "Labour Market",
                        "Digital Transformation",
                    ],
                ),
            ],
            "template": """Perform an industry trend analysis.

Industry: {industry}
Region: {region}
Time Horizon: {time_horizon}
Trend Focus: {trend_focus}

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
            "fields": [
                field("Business", "business"),
                field("Product / Service", "product_service"),
                field("Period", "period"),
                field("Sales Data / Observations", "sales_data_observations", "text_area"),
                field(
                    "Sales Channel",
                    "sales_channel",
                    "multiselect",
                    ["Direct Sales", "Website", "Marketplace", "Retail", "Wholesale", "Social Media", "Referrals", "Partnerships", "B2B", "B2C"],
                ),
                field(
                    "Sales Focus",
                    "sales_focus",
                    "multiselect",
                    ["Revenue Growth", "Conversion Rate", "Average Order Value", "Customer Acquisition", "Customer Retention", "Sales Funnel", "Pricing", "Forecasting"],
                ),
            ],
            "template": """Analyze sales performance.

Business: {business}
Product / Service: {product_service}
Period: {period}
Sales Data / Observations: {sales_data_observations}
Sales Channel: {sales_channel}
Sales Focus: {sales_focus}

Provide:

1. Revenue trend analysis
2. Customer segment analysis
3. Underperforming areas
4. Growth opportunities
5. Sales funnel improvements
6. KPI recommendations
7. Action plan""",
        },
    ],
    "Construction": [
        {
            "category": "Construction",
            "name": "Project Plan",
            "fields": [
                field("Project", "project"),
                field("State", "state", "selectbox", STATE_OPTIONS),
                field("Location", "location"),
                field("Building Type", "building_type", "selectbox", BUILDING_TYPE_OPTIONS),
                field("Building Class", "building_class", "selectbox", BUILDING_CLASS_OPTIONS),
                field("Contract Type", "contract_type", "selectbox", CONTRACT_TYPE_OPTIONS),
                field("Budget Range", "budget_range", "selectbox", ["Under $250k", "$250k-$500k", "$500k-$1m", "$1m-$5m", "$5m-$20m", "$20m+"]),
                field("Duration", "duration"),
                field("Key Constraints", "key_constraints", "text_area"),
            ],
            "template": """Create a construction project execution plan.

Project: {project}
State: {state}
Location: {location}
Building Type: {building_type}
Building Class: {building_class}
Contract Type: {contract_type}
Budget: {budget_range}
Duration: {duration}
Key Constraints: {key_constraints}

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
            "fields": [
                field("Project", "project"),
                field("State", "state", "selectbox", STATE_OPTIONS),
                field("Building Class", "building_class", "selectbox", BUILDING_CLASS_OPTIONS),
                field("Building Type", "building_type", "selectbox", BUILDING_TYPE_OPTIONS),
                field("Scope of Works", "scope_of_works", "text_area"),
                field(
                    "Compliance Focus",
                    "compliance_focus",
                    "multiselect",
                    [
                        "Fire Safety",
                        "Structure",
                        "Waterproofing",
                        "Energy Efficiency",
                        "Accessibility",
                        "Livable Housing",
                        "Ventilation",
                        "Damp and Weatherproofing",
                        "Bushfire",
                        "Balustrades / Stairs",
                        "Wet Areas",
                        "Glazing",
                        "Roof Drainage",
                    ],
                ),
            ],
            "template": """Review this construction scenario against Australian NCC and Housing Provisions.

Project: {project}
State: {state}
Building Class: {building_class}
Building Type: {building_type}
Scope of Works: {scope_of_works}
Compliance Focus: {compliance_focus}

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
            "fields": [
                field("Project", "project"),
                field("State", "state", "selectbox", STATE_OPTIONS),
                field("Building Class", "building_class", "selectbox", BUILDING_CLASS_OPTIONS),
                field("Building Type", "building_type", "selectbox", BUILDING_TYPE_OPTIONS),
                field(
                    "Design Stage",
                    "design_stage",
                    "selectbox",
                    ["Concept Design", "Design Development", "Building Permit", "Construction Documentation", "Construction Stage", "Completion / Occupancy"],
                ),
                field("Scope", "scope", "text_area"),
                field(
                    "NCC 2025 Focus",
                    "ncc_2025_focus",
                    "multiselect",
                    ["Energy Efficiency", "Livable Housing", "Waterproofing", "Condensation", "Fire Safety", "Structure", "Accessibility", "Ventilation", "Documentation", "Performance Solution"],
                ),
            ],
            "template": """Review this project for potential NCC 2025 compliance issues.

Project: {project}
State: {state}
Building Class: {building_class}
Building Type: {building_type}
Design Stage: {design_stage}
Scope: {scope}
NCC 2025 Focus: {ncc_2025_focus}

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
            "fields": [
                field("Project", "project"),
                field("State", "state", "selectbox", STATE_OPTIONS),
                field("Trade / Scope", "trade_scope"),
                field("Stage of Works", "stage_of_works", "selectbox", STAGE_OF_WORKS_OPTIONS),
                field(
                    "Supervision Focus",
                    "supervision_focus",
                    "multiselect",
                    ["Quality", "Safety", "Programme", "Trade Coordination", "Defects", "Hold Points", "Site Documentation", "Subcontractor Management"],
                ),
            ],
            "template": """Create a construction site supervision plan.

Project: {project}
State: {state}
Trade / Scope: {trade_scope}
Stage of Works: {stage_of_works}
Supervision Focus: {supervision_focus}

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
            "fields": [
                field("Project", "project"),
                field("Date / Week", "date_week"),
                field("Completed Works", "completed_works", "text_area"),
                field("Current Activities", "current_activities", "text_area"),
                field("Delays / Issues", "delays_issues", "text_area"),
                field("Upcoming Works", "upcoming_works", "text_area"),
                field("Progress Status", "progress_status", "selectbox", ["On Track", "Minor Delay", "Major Delay", "At Risk", "Accelerated"]),
            ],
            "template": """Generate a professional construction site progress report.

Project: {project}
Date / Week: {date_week}
Completed Works: {completed_works}
Current Activities: {current_activities}
Delays / Issues: {delays_issues}
Upcoming Works: {upcoming_works}
Progress Status: {progress_status}

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
            "fields": [
                field("Project", "project"),
                field("State", "state", "selectbox", STATE_OPTIONS),
                field("Scope", "scope", "text_area"),
                field("Stage", "stage", "selectbox", STAGE_OF_WORKS_OPTIONS),
                field("Risk Level", "risk_level", "selectbox", RISK_LEVEL_OPTIONS),
                field(
                    "Risk Categories",
                    "risk_categories",
                    "multiselect",
                    ["Safety", "Cost", "Schedule", "Quality", "Environmental", "Legal / Compliance", "Design", "Procurement", "Weather", "Subcontractor Performance"],
                ),
            ],
            "template": """Perform a construction risk assessment.

Project: {project}
State: {state}
Scope: {scope}
Stage: {stage}
Risk Level: {risk_level}
Risk Categories: {risk_categories}

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
            "fields": [
                field("Project", "project"),
                field("Building Type", "building_type", "selectbox", BUILDING_TYPE_OPTIONS),
                field("Floor Area", "floor_area"),
                field("State", "state", "selectbox", STATE_OPTIONS),
                field("Scope", "scope", "text_area"),
                field(
                    "Estimate Type",
                    "estimate_type",
                    "selectbox",
                    ["Preliminary Estimate", "Concept Estimate", "Detailed Estimate", "Tender Estimate", "Variation Estimate", "Final Cost Report"],
                ),
                field(
                    "Cost Focus",
                    "cost_focus",
                    "multiselect",
                    ["Labour", "Materials", "Plant", "Subcontractors", "Preliminaries", "Contingency", "Escalation", "Risk Allowance", "GST", "Professional Fees"],
                ),
            ],
            "template": """Prepare a preliminary construction cost estimate.

Project: {project}
Building Type: {building_type}
Floor Area: {floor_area}
State: {state}
Scope: {scope}
Estimate Type: {estimate_type}
Cost Focus: {cost_focus}

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
            "fields": [
                field("Project", "project"),
                field("Site", "site"),
                field("Date", "date"),
                field("Observations", "observations", "text_area"),
                field(
                    "Safety Focus",
                    "safety_focus",
                    "multiselect",
                    [
                        "Working at Heights",
                        "Electrical",
                        "Excavation",
                        "Plant and Equipment",
                        "Manual Handling",
                        "Traffic Management",
                        "PPE",
                        "Housekeeping",
                        "Scaffolding",
                        "Ladders",
                        "Silica / Dust",
                        "Hot Works",
                        "Confined Space",
                    ],
                ),
                field("Risk Level", "risk_level", "selectbox", RISK_LEVEL_OPTIONS),
            ],
            "template": """Generate a construction safety inspection report.

Project: {project}
Site: {site}
Date: {date}
Observations: {observations}
Safety Focus: {safety_focus}
Risk Level: {risk_level}

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
            "fields": [
                field("Project", "project"),
                field("Date", "date"),
                field("Topic", "topic"),
                field("Attendees", "attendees", "text_area"),
                field(
                    "Toolbox Topic",
                    "toolbox_topic",
                    "selectbox",
                    [
                        "Working at Heights",
                        "Manual Handling",
                        "Electrical Safety",
                        "Excavation Safety",
                        "Plant and Equipment",
                        "Traffic Management",
                        "PPE",
                        "Silica Dust",
                        "Housekeeping",
                        "Weather Conditions",
                        "Emergency Procedures",
                        "Site Induction",
                    ],
                ),
            ],
            "template": """Generate a toolbox meeting agenda and record.

Project: {project}
Date: {date}
Topic: {topic}
Attendees: {attendees}
Toolbox Topic: {toolbox_topic}

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
            "fields": [
                field("Project", "project"),
                field("State", "state", "selectbox", STATE_OPTIONS),
                field("Contract Type", "contract_type", "selectbox", CONTRACT_TYPE_OPTIONS),
                field("Issue", "issue", "text_area"),
                field(
                    "Legal Focus",
                    "legal_focus",
                    "multiselect",
                    ["Payment Claims", "Security of Payment", "Variations", "EOT", "Defects", "Latent Conditions", "Liquidated Damages", "Termination", "WHS", "Licensing", "Insurance", "Dispute Resolution"],
                ),
            ],
            "template": """Analyze applicable construction laws and regulatory risks.

Project: {project}
State: {state}
Contract Type: {contract_type}
Issue: {issue}
Legal Focus: {legal_focus}

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
            "fields": [
                field("Project", "project"),
                field("Client", "client"),
                field("Contract Type", "contract_type", "selectbox", CONTRACT_TYPE_OPTIONS),
                field("Tender Scope", "tender_scope", "text_area"),
                field("Tender Value", "tender_value"),
                field(
                    "Review Focus",
                    "review_focus",
                    "multiselect",
                    ["Commercial Risk", "Technical Risk", "Scope Gap", "Programme Risk", "Liquidated Damages", "Payment Terms", "Design Responsibility", "Latent Conditions", "Exclusions", "Clarifications"],
                ),
            ],
            "template": """Review the following construction tender submission.

Project: {project}
Client: {client}
Contract Type: {contract_type}
Tender Scope: {tender_scope}
Tender Value: {tender_value}
Review Focus: {review_focus}

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
            "fields": [
                field("Project", "project"),
                field("Drawing / Specification Reference", "drawing_specification_reference"),
                field("Issue", "issue", "text_area"),
                field("Impact", "impact", "text_area"),
                field(
                    "RFI Type",
                    "rfi_type",
                    "selectbox",
                    ["Design Clarification", "Specification Conflict", "Drawing Discrepancy", "Site Condition", "Material Substitution", "Coordination Issue", "Programme Impact", "Cost Impact"],
                ),
            ],
            "template": """Create a professional Request for Information.

Project: {project}
Drawing / Specification Reference: {drawing_specification_reference}
Issue: {issue}
Impact: {impact}
RFI Type: {rfi_type}

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
            "fields": [
                field("Project", "project"),
                field("Contract Type", "contract_type", "selectbox", CONTRACT_TYPE_OPTIONS),
                field("Variation Description", "variation_description", "text_area"),
                field("Cause", "cause", "text_area"),
                field("Cost Impact", "cost_impact"),
                field("Time Impact", "time_impact"),
                field(
                    "Variation Type",
                    "variation_type",
                    "selectbox",
                    ["Client Instruction", "Design Change", "Latent Condition", "Scope Gap", "Regulatory Requirement", "Site Condition", "Delay Event", "Material Substitution"],
                ),
            ],
            "template": """Prepare a construction variation claim.

Project: {project}
Contract: {contract_type}
Variation Description: {variation_description}
Cause: {cause}
Cost Impact: {cost_impact}
Time Impact: {time_impact}
Variation Type: {variation_type}

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
            "fields": [
                field("Subcontractor", "subcontractor"),
                field(
                    "Trade",
                    "trade",
                    "selectbox",
                    ["Demolition", "Excavation", "Concrete", "Steel", "Carpentry", "Roofing", "Cladding", "Waterproofing", "Plumbing", "Electrical", "HVAC", "Fire Services", "Plastering", "Painting", "Tiling", "Flooring", "Landscaping", "Joinery", "Glazing"],
                ),
                field("Project", "project"),
                field("Performance Observations", "performance_observations", "text_area"),
                field(
                    "Evaluation Focus",
                    "evaluation_focus",
                    "multiselect",
                    ["Quality", "Safety", "Programme", "Communication", "Commercial", "Defects", "Documentation", "Coordination", "Responsiveness"],
                ),
            ],
            "template": """Evaluate a subcontractor.

Subcontractor: {subcontractor}
Trade: {trade}
Project: {project}
Performance Observations: {performance_observations}
Evaluation Focus: {evaluation_focus}

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
            "fields": [
                field("Project", "project"),
                field("Contract Type", "contract_type", "selectbox", CONTRACT_TYPE_OPTIONS),
                field("Clause / Issue", "clause_issue", "text_area"),
                field("Concern", "concern", "text_area"),
                field(
                    "Contract Focus",
                    "contract_focus",
                    "multiselect",
                    ["Key Obligations", "Risk Clauses", "Payment Terms", "Variations", "EOT", "Delay Damages", "Defects", "Dispute Resolution", "Termination", "Insurance", "Warranties", "Scope Exclusions"],
                ),
            ],
            "template": """Analyze this construction contract.

Project: {project}
Contract Type: {contract_type}
Clause / Issue: {clause_issue}
Concern: {concern}
Contract Focus: {contract_focus}

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
            "fields": [
                field("Project", "project"),
                field("Stage", "stage", "selectbox", STAGE_OF_WORKS_OPTIONS),
                field(
                    "Current BIM Platform",
                    "current_bim_platform",
                    "selectbox",
                    ["Revit", "Navisworks", "ArchiCAD", "Tekla", "BIM360", "Autodesk Construction Cloud", "Procore", "Bluebeam", "Other"],
                ),
                field("Main Problems", "main_problems", "text_area"),
                field(
                    "BIM / AI Focus",
                    "bim_ai_focus",
                    "multiselect",
                    ["Clash Detection", "Quantity Takeoff", "Programme Analysis", "Cost Control", "Site Reporting", "Defect Detection", "Document Control", "Safety Analytics", "Digital Twin", "Procurement Automation"],
                ),
            ],
            "template": """Analyze BIM and AI opportunities for this construction project.

Project: {project}
Stage: {stage}
Current BIM Platform: {current_bim_platform}
Main Problems: {main_problems}
BIM / AI Focus: {bim_ai_focus}

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
            "fields": [
                field("Project", "project"),
                field(
                    "Asset Type",
                    "asset_type",
                    "selectbox",
                    ["Residential Building", "Commercial Building", "Industrial Facility", "Hospital", "School", "Retail Centre", "Infrastructure Asset", "Civil Asset", "Mixed-use Development"],
                ),
                field("Project Stage", "project_stage", "selectbox", STAGE_OF_WORKS_OPTIONS),
                field("Available Data", "available_data", "text_area"),
                field(
                    "Digital Twin Focus",
                    "digital_twin_focus",
                    "multiselect",
                    ["Asset Management", "Maintenance", "Energy Performance", "Occupancy", "Safety", "IoT Sensors", "BIM Integration", "Operations", "Lifecycle Cost"],
                ),
            ],
            "template": """Create a digital twin strategy for a construction or asset project.

Project: {project}
Asset Type: {asset_type}
Project Stage: {project_stage}
Available Data: {available_data}
Digital Twin Focus: {digital_twin_focus}

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
            "fields": [
                field("Project", "project"),
                field("Building Type", "building_type", "selectbox", BUILDING_TYPE_OPTIONS),
                field("State", "state", "selectbox", STATE_OPTIONS),
                field("Scope", "scope", "text_area"),
                field(
                    "Prefab Focus",
                    "prefab_focus",
                    "multiselect",
                    ["Bathroom Pods", "Wall Panels", "Roof Trusses", "Structural Steel", "Precast Concrete", "Modular Rooms", "Services Risers", "Facade Panels", "Programme Reduction", "Waste Reduction"],
                ),
            ],
            "template": """Assess prefabrication or modular construction opportunities.

Project: {project}
Building Type: {building_type}
State: {state}
Scope: {scope}
Prefab Focus: {prefab_focus}

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
            "fields": [
                field("Project", "project"),
                field("Trade / Scope", "trade_scope"),
                field("Current Bottlenecks", "current_bottlenecks", "text_area"),
                field(
                    "Productivity Focus",
                    "productivity_focus",
                    "multiselect",
                    ["Labour Utilisation", "Material Handling", "Trade Sequencing", "Site Logistics", "Rework Reduction", "Digital Tools", "AI Automation", "Standardisation", "Lean Construction"],
                ),
            ],
            "template": """Create a construction productivity improvement plan.

Project: {project}
Trade / Scope: {trade_scope}
Current Bottlenecks: {current_bottlenecks}
Productivity Focus: {productivity_focus}

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
            "fields": [
                field("Project", "project"),
                field("Area", "area"),
                field("Inspection Date", "inspection_date"),
                field("Observed Defects", "observed_defects", "text_area"),
                field(
                    "Defect Category",
                    "defect_category",
                    "selectbox",
                    ["Waterproofing", "Structural", "Finishes", "Plumbing", "Electrical", "Fire Services", "Doors / Windows", "Cladding", "Roofing", "Painting", "Tiling", "Flooring", "Joinery", "Documentation"],
                ),
                field("Severity", "severity", "selectbox", RISK_LEVEL_OPTIONS),
            ],
            "template": """Generate a defect and quality inspection report.

Project: {project}
Area: {area}
Inspection Date: {inspection_date}
Observed Defects: {observed_defects}
Defect Category: {defect_category}
Severity: {severity}

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
            "fields": [
                field("Project", "project"),
                field("Key Materials", "key_materials", "text_area"),
                field("Suppliers", "suppliers", "text_area"),
                field("Programme Requirements", "programme_requirements", "text_area"),
                field(
                    "Procurement Focus",
                    "procurement_focus",
                    "multiselect",
                    ["Long-lead Items", "Supplier Risk", "Price Escalation", "Logistics", "Substitution Options", "Local Availability", "Quality Risk", "Storage", "Delivery Sequencing", "Contract Terms"],
                ),
            ],
            "template": """Review procurement risks for a construction project.

Project: {project}
Key Materials: {key_materials}
Suppliers: {suppliers}
Programme Requirements: {programme_requirements}
Procurement Focus: {procurement_focus}

Provide:

1. Long-lead items
2. Supplier risks
3. Price escalation risks
4. Logistics risks
5. Alternative procurement options
6. Mitigation strategy
7. Procurement action plan""",
        },
    ],
}


def run_fast_mode(query: str) -> dict:
    from crewai import Crew, Task

    import intelligent_gateway

    task = Task(
        description=query,
        expected_output="A professional detailed response.",
        agent=intelligent_gateway.writer_agent,
    )
    crew = Crew(
        agents=[intelligent_gateway.writer_agent],
        tasks=[task],
        verbose=True,
    )

    try:
        result = crew.kickoff()
    except Exception:
        return {
            "category": "writing",
            "confidence": 1.0,
            "result": "Gateway execution failed: unable to reach the LLM provider. Please try again later.",
            "version": VERSION,
        }

    try:
        output = result.raw
    except AttributeError:
        output = str(result)

    return {
        "category": "writing",
        "confidence": 1.0,
        "result": output,
        "version": VERSION,
    }


def run_advanced_mode(query: str) -> dict:
    response = requests.post(
        API_URL,
        json={"query": query},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def save_history_entry(query: str, mode_name: str, payload: dict, elapsed_seconds: float) -> dict:
    entry = {
        "query": query,
        "mode": mode_name,
        "category": payload.get("category", ""),
        "confidence": payload.get("confidence", ""),
        "version": payload.get("version", ""),
        "result": payload.get("result", ""),
        "elapsed_seconds": elapsed_seconds,
    }
    st.session_state.history.insert(0, entry)
    st.session_state.history = st.session_state.history[:HISTORY_LIMIT]
    st.session_state.selected_history = entry
    return entry


def display_result(entry: dict) -> None:
    st.subheader("Response")
    st.write(f"Mode: {entry.get('mode', '')}")
    st.write(f"Response Time: {entry.get('elapsed_seconds', 0.0):.1f}s")
    st.write("category")
    st.code(str(entry.get("category", "")))
    st.write("confidence")
    st.code(str(entry.get("confidence", "")))
    st.write("version")
    st.code(str(entry.get("version", "")))
    st.write("result")
    st.write(entry.get("result", ""))


def format_form_value(value: str | list[str]) -> str:
    if isinstance(value, list):
        return ", ".join(value) if value else "Not specified"
    return value.strip() if value.strip() else "Not specified"


def build_prompt_from_form(form_definition: dict, values: dict[str, str | list[str]]) -> str:
    formatted_values = {
        key: format_form_value(value)
        for key, value in values.items()
    }
    return form_definition["template"].format(**formatted_values)


def extract_pdf_text(file_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx_text(file_bytes: bytes) -> str:
    from docx import Document

    document = Document(BytesIO(file_bytes))
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    for table in document.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells)
            if row_text.strip():
                parts.append(row_text)
    return "\n".join(parts)


def extract_xlsx_text(file_bytes: bytes) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    parts = []
    for worksheet in workbook.worksheets:
        parts.append(f"Sheet: {worksheet.title}")
        for row in worksheet.iter_rows(values_only=True):
            row_values = [str(value) for value in row if value is not None]
            if row_values:
                parts.append(" | ".join(row_values))
    workbook.close()
    return "\n".join(parts)


def extract_uploaded_document_text(file_name: str, file_bytes: bytes) -> str:
    suffix = file_name.rsplit(".", 1)[-1].lower()
    if suffix == "pdf":
        return extract_pdf_text(file_bytes)
    if suffix == "txt":
        return file_bytes.decode("utf-8")
    if suffix == "docx":
        return extract_docx_text(file_bytes)
    if suffix == "xlsx":
        return extract_xlsx_text(file_bytes)
    raise ValueError("Unsupported file type.")


def truncate_document_text(document_text: str) -> tuple[str, bool]:
    if len(document_text) <= DOCUMENT_TEXT_LIMIT:
        return document_text, False
    return document_text[:DOCUMENT_TEXT_LIMIT], True


def build_document_prompt(
    analysis_type: str,
    file_name: str,
    document_text: str,
    truncated: bool,
) -> str:
    truncation_notice = ""
    if truncated:
        truncation_notice = f"Content truncated to first {DOCUMENT_TEXT_LIMIT} characters.\n\n"
    report_items = DOCUMENT_REPORT_STRUCTURES.get(
        analysis_type,
        DOCUMENT_REPORT_STRUCTURES["Business Analysis"],
    )
    report_structure = "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(report_items, start=1)
    )

    return f"""Analyze the following uploaded document.

Analysis Type: {analysis_type}
File Name: {file_name}

Document Content:
{truncation_notice}{document_text}

Provide:
{report_structure}"""


def render_document_analysis() -> None:
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=["pdf", "txt", "docx", "xlsx"],
        key="document_analysis_upload",
    )
    analysis_type = st.selectbox(
        "Analysis Type",
        DOCUMENT_ANALYSIS_TYPES,
        key="document_analysis_type",
    )

    document_text = ""
    truncated_text = ""
    truncated = False
    read_failed = False

    if uploaded_file:
        try:
            document_text = extract_uploaded_document_text(
                uploaded_file.name,
                uploaded_file.getvalue(),
            )
            truncated_text, truncated = truncate_document_text(document_text)
        except Exception as exc:
            read_failed = True
            st.error(f"Could not read uploaded file: {exc}")
        else:
            st.write(f"File name: {uploaded_file.name}")
            st.write(f"Extracted character count: {len(document_text)}")
            st.write(f"Truncated: {'Yes' if truncated else 'No'}")

    if st.button("Generate Document Prompt", use_container_width=True):
        if not uploaded_file:
            st.warning("Please upload a document first.")
        elif read_failed:
            st.error("Could not generate a prompt because the uploaded file could not be read.")
        else:
            st.session_state.query = build_document_prompt(
                analysis_type,
                uploaded_file.name,
                truncated_text,
                truncated,
            )


def render_form_builder() -> None:
    selected_category = st.selectbox(
        "Form Category",
        list(FORM_LIBRARY.keys()),
        key="form_builder_category",
    )
    form_definitions = FORM_LIBRARY[selected_category]
    form_names = [form_definition["name"] for form_definition in form_definitions]
    selected_form_name = st.selectbox(
        "Form",
        form_names,
        key="form_builder_form",
    )
    selected_form = next(
        form_definition
        for form_definition in form_definitions
        if form_definition["name"] == selected_form_name
    )

    with st.form("prompt_form_builder"):
        values = {}
        for form_field in selected_form["fields"]:
            widget_key = f"form_builder_{selected_category}_{selected_form_name}_{form_field['key']}"
            field_type = form_field["type"]

            if field_type == "text_area":
                values[form_field["key"]] = st.text_area(
                    form_field["name"],
                    key=widget_key,
                    height=80,
                )
            elif field_type == "selectbox":
                values[form_field["key"]] = st.selectbox(
                    form_field["name"],
                    form_field["options"],
                    key=widget_key,
                )
            elif field_type == "multiselect":
                values[form_field["key"]] = st.multiselect(
                    form_field["name"],
                    form_field["options"],
                    key=widget_key,
                )
            else:
                values[form_field["key"]] = st.text_input(
                    form_field["name"],
                    key=widget_key,
                )

        if st.form_submit_button("Generate Prompt", use_container_width=True):
            st.session_state.query = build_prompt_from_form(selected_form, values)


st.set_page_config(page_title="Garrett Intelligence Hub", page_icon=":material/hub:")

if "history" not in st.session_state:
    st.session_state.history = []

if "selected_history" not in st.session_state:
    st.session_state.selected_history = None

if "query" not in st.session_state:
    st.session_state.query = ""

prompt_store.initialize_prompt_store()

st.title("Garrett Intelligence Hub")

with st.sidebar:
    with st.expander("Prompt Library", expanded=True):
        categories = prompt_store.list_categories()
        if categories:
            selected_category = st.selectbox("Category", categories, key="prompt_library_category")
            prompts = prompt_store.list_prompts(selected_category)
            prompt_options = {prompt["name"]: prompt["id"] for prompt in prompts}

            selected_prompt_name = st.selectbox(
                "Prompt",
                list(prompt_options.keys()),
                key="prompt_library_prompt",
            )
            selected_prompt_id = prompt_options[selected_prompt_name]

            if st.button("Load Template", use_container_width=True):
                selected_prompt = prompt_store.get_prompt(selected_prompt_id)
                if selected_prompt:
                    st.session_state.query = selected_prompt["content"]
        else:
            st.caption("No prompts available.")

    with st.expander("Form Builder", expanded=False):
        render_form_builder()

    with st.expander("Document Analysis", expanded=False):
        render_document_analysis()

    with st.expander("History", expanded=True):
        st.download_button(
            "Export History",
            data=json.dumps(st.session_state.history, indent=2),
            file_name="history.json",
            mime="application/json",
            use_container_width=True,
        )

        if st.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.session_state.selected_history = None

        if st.session_state.history:
            for index, entry in enumerate(st.session_state.history[:HISTORY_LIMIT]):
                label = entry["query"].replace("\n", " ").strip()
                if len(label) > 60:
                    label = f"{label[:57]}..."
                if st.button(
                    f"{index + 1}. {entry['mode']} - {label}",
                    key=f"history_{index}",
                    use_container_width=True,
                ):
                    st.session_state.selected_history = entry
        else:
            st.caption("No history yet.")

mode = st.radio(
    "Routing",
    ["Fast Mode", "Advanced Agent Routing"],
    index=0,
    horizontal=True,
)
is_fast_mode = mode == "Fast Mode"
mode_name = "Fast" if is_fast_mode else "Advanced"
st.write(f"Mode: {mode_name}")

query = st.text_area(
    "Input",
    height=160,
    placeholder="Enter a request for the gateway...",
    key="query",
)
submitted = st.button("Submit", type="primary")
display_entry = st.session_state.selected_history

if submitted:
    cleaned_query = query.strip()

    if not cleaned_query:
        st.warning("Please enter a request.")
    else:
        try:
            with st.spinner("Analyzing..."):
                started_at = time.perf_counter()
                if is_fast_mode:
                    payload = run_fast_mode(cleaned_query)
                else:
                    payload = run_advanced_mode(cleaned_query)
                elapsed_seconds = time.perf_counter() - started_at
        except requests.exceptions.RequestException as exc:
            st.error(f"Request failed: {exc}")
        except ValueError:
            st.error("Request failed: FastAPI returned invalid JSON.")
        else:
            display_entry = save_history_entry(
                cleaned_query,
                mode_name,
                payload,
                elapsed_seconds,
            )

if display_entry:
    display_result(display_entry)
