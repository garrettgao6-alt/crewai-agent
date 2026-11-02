import json
from io import BytesIO
import os
from datetime import timedelta
from xml.sax.saxutils import escape
import time
from uuid import uuid4

import requests
import streamlit as st

st.set_page_config(
    page_title="Gao Intelligence Hub",
    layout="wide",
    initial_sidebar_state="auto",
)

# This dependency emits a migration notice at import. Keep it in server logs,
# outside the product layout; cookie validation and encryption are unchanged.
_cookie_import_notice=st.empty()
with _cookie_import_notice.container():
    from streamlit_cookies_manager import EncryptedCookieManager
_cookie_import_notice.empty()

from core.document_pipeline import process_document
from core.engine import run_engine
from core.ncc_parser import clauses_to_documents, parse_ncc_clauses
from core.vector_store import build_context, format_sources
import project_store
import report_store
from core.ingestion import ingest_document
from core import ncc_library
from public_demo_ui import render_demo
import prompt_store
import subscription_store
import template_store
import user_store


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/analyze")
REQUEST_TIMEOUT_SECONDS = 60
VERSION = "1.0"
HISTORY_LIMIT = 10
DEFAULT_SECTION = "Dashboard"
COOKIE_PREFIX = "gao_app"
COOKIE_USER_ID_KEY = "user_id"  # Legacy cookie is cleared; never accepted for authentication.
COOKIE_SESSION_KEY = "session_token"
COPILOT_SESSION_CALL_LIMIT = 50
GUEST_COPILOT_SESSION_LIMIT = 3
DOCUMENT_TEXT_LIMIT = 12000
DOCUMENT_TOTAL_TEXT_LIMIT = 30000
GUEST_USER = {
    "id": "guest",
    "username": "Guest",
    "role": "guest",
}
NAVIGATION_OPTIONS = [
    "Dashboard",
    "Copilot",
    "Documents",
    "BIM",
    "Reports",
    "Settings",
]
SECTION_TO_NAVIGATION = {
    section: section
    for section in NAVIGATION_OPTIONS
}
SECTION_ALIASES = {
    "workspace": DEFAULT_SECTION,
    "dashboard": DEFAULT_SECTION,
    "upload": "Documents",
    "documents": "Documents",
    "bim": "BIM",
    "ai": "Copilot",
    "copilot": "Copilot",
    "logs": "Reports",
    "reports": "Reports",
    "settings": "Settings",
}
NAVIGATION_ICONS = {
    "Dashboard": "□",
    "Copilot": "◇",
    "Documents": "▤",
    "BIM": "▦",
    "Reports": "◈",
    "Settings": "○",
}
DOCUMENT_ANALYSIS_TYPES = [
    "Contract Review",
    "Tender Review",
    "Risk Assessment",
    "Meeting Minutes",
    "Progress Report",
    "Safety Inspection",
    "Business Analysis",
]
PROJECT_REVIEW_TYPES = [
    "Full Project Review",
    "Contract + Tender Review",
    "Commercial Risk Review",
    "Construction Risk Review",
    "NCC / Compliance Review",
    "Procurement Review",
    "Progress & Meeting Review",
]
EXECUTIVE_AGENT_MODES = [
    "Fast Executive Review",
    "Full Board Review",
    "Deep Due Diligence",
]
EXECUTIVE_AGENT_MODE_DESCRIPTIONS = {
    "Fast Executive Review": "Runs only the Executive Coordinator Agent. Fastest and lowest cost.",
    "Full Board Review": "Runs Contract, Risk, Finance, and Executive Coordinator agents. Balanced speed and quality.",
    "Deep Due Diligence": "Runs all executive agents. Strongest analysis and highest cost for important projects.",
}
DOCUMENT_REPORT_STRUCTURES = {
    "Contract Review": [
        "Executive Summary",
        "Key Obligations",
        "Payment Risks",
        "Variation Risks",
        "EOT / Delay Risks",
        "Dispute Clauses",
        "Red Flags",
        "Recommended Actions",
    ],
    "Tender Review": [
        "Tender Summary",
        "Scope Gaps",
        "Commercial Risks",
        "Technical Risks",
        "Clarification Questions",
        "Go / No-Go Recommendation",
    ],
    "Risk Assessment": [
        "Risk Register",
        "Safety Risks",
        "Commercial Risks",
        "Programme Risks",
        "Legal / Compliance Risks",
        "Mitigation Actions",
        "Priority Matrix",
    ],
    "Meeting Minutes": [
        "Meeting Summary",
        "Key Decisions",
        "Action Items",
        "Responsible Parties",
        "Due Dates",
        "Follow-up Items",
    ],
    "Progress Report": [
        "Executive Summary",
        "Completed Works",
        "Current Activities",
        "Delays / Issues",
        "Safety / Quality Notes",
        "Upcoming Works",
        "Action Items",
    ],
    "Safety Inspection": [
        "Hazards Identified",
        "Risk Rating",
        "Corrective Actions",
        "Responsible Person",
        "Due Date",
        "Follow-up Requirements",
    ],
    "Business Analysis": [
        "Executive Summary",
        "Key Findings",
        "Business Risks",
        "Opportunities",
        "Recommendations",
        "Next Steps",
    ],
}
DOCUMENT_PDF_FILENAMES = {
    "Contract Review": "contract_review.pdf",
    "Tender Review": "tender_review.pdf",
    "Risk Assessment": "risk_assessment.pdf",
    "Meeting Minutes": "meeting_minutes.pdf",
    "Progress Report": "progress_report.pdf",
    "Safety Inspection": "safety_inspection.pdf",
    "Business Analysis": "business_analysis.pdf",
}
PROJECT_REVIEW_PDF_FILENAMES = {
    "Full Project Review": "full_project_review.pdf",
    "Contract + Tender Review": "contract_tender_review.pdf",
    "Commercial Risk Review": "commercial_risk_review.pdf",
    "Construction Risk Review": "construction_risk_review.pdf",
    "NCC / Compliance Review": "ncc_compliance_review.pdf",
    "Procurement Review": "procurement_review.pdf",
    "Progress & Meeting Review": "progress_meeting_review.pdf",
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


def field(
    name: str,
    key: str,
    field_type: str = "text_input",
    options: list[str] | None = None,
    placeholder: str = "",
) -> dict:
    return {
        "name": name,
        "key": key,
        "type": field_type,
        "options": options or [],
        "placeholder": placeholder,
    }


AUTOMATION_TOOLS = [
    "Excel",
    "Google Sheets",
    "Microsoft Project",
    "Notion",
    "Trello",
    "Asana",
    "Monday.com",
    "Slack",
    "Gmail",
    "Outlook",
    "Google Drive",
    "OneDrive",
    "Dropbox",
    "Canva",
    "Buffer",
    "Zapier",
    "Make",
    "Python",
    "Power BI",
    "Tableau",
    "Streamlit",
    "Other",
]
AUTOMATION_OUTPUT_FORMATS = [
    "Step-by-step SOP",
    "Workflow Plan",
    "Automation Blueprint",
    "Checklist",
    "Report",
    "Dashboard Plan",
    "Content Calendar",
    "Email Campaign Plan",
    "Gantt Chart Plan",
]
AUTOMATION_COMMON_FIELDS = [
    field("Business / Project Name", "business_project_name"),
    field("Industry", "industry"),
    field("Goal", "goal", "text_area"),
    field("Current Process", "current_process", "text_area"),
    field("Tools Used", "tools_used", "multiselect", AUTOMATION_TOOLS),
    field("Output Format", "output_format", "selectbox", AUTOMATION_OUTPUT_FORMATS),
]


FORM_LIBRARY = {
    "Business": [
        {
            "category": "Business",
            "name": "Market Research",
            "fields": [
                field("Industry", "industry", "selectbox", INDUSTRY_OPTIONS),
                field("Region / Country", "region_country", placeholder="e.g. Australia, New Zealand, United States"),
                field("Target Customers", "target_customers", placeholder="e.g. Residential builders, developers, contractors"),
                field("Product / Service", "product_service", placeholder="e.g. Construction project management platform"),
                field("Market Segment", "market_segment", placeholder="e.g. Residential Construction"),
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


AUTOMATION_LIBRARY = [
    {
        "name": "Project Management Automation",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("Project Type", "project_type", "selectbox", ["Construction Project", "Software Project", "Marketing Project", "Business Operations", "Product Launch", "Internal Workflow", "Other"]),
            field("Team Size", "team_size"),
            field("Reporting Frequency", "reporting_frequency", "selectbox", ["Daily", "Weekly", "Fortnightly", "Monthly"]),
            field("Current Project Management Tool", "current_project_management_tool"),
            field("Pain Points", "pain_points", "text_area"),
            field(
                "Automation Scope",
                "automation_scope",
                "multiselect",
                ["Task Assignment", "Status Reporting", "Risk Register", "Issue Tracking", "Meeting Notes", "Progress Dashboard", "Reminder Automation", "Document Control"],
            ),
        ],
        "output_sections": [
            "Executive Summary",
            "Current PM Workflow Assessment",
            "Automated Task Breakdown",
            "RACI Responsibility Matrix",
            "Risk / Issue Tracking Workflow",
            "Weekly Reporting Automation",
            "Tool Setup Recommendation",
            "Implementation Checklist",
            "KPI Metrics",
        ],
        "template": """Create a professional project management automation blueprint.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

Project Type: {project_type}
Team Size: {team_size}
Reporting Frequency: {reporting_frequency}
Current Project Management Tool: {current_project_management_tool}
Pain Points: {pain_points}
Automation Scope: {automation_scope}

Design a practical automation system that improves project control, reporting, accountability, and follow-up without requiring unsupported API access.

Provide:
{output_sections}

Include this table:
Task | Owner | Frequency | Trigger | Automation Tool | Output""",
    },
    {
        "name": "Gantt Chart Planner",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("Project Start Date", "project_start_date"),
            field("Project End Date", "project_end_date"),
            field("Major Phases", "major_phases", "text_area"),
            field("Key Milestones", "key_milestones", "text_area"),
            field("Resource Constraints", "resource_constraints", "text_area"),
            field("Dependency Notes", "dependency_notes", "text_area"),
        ],
        "output_sections": [
            "Work Breakdown Structure",
            "Phase Plan",
            "Milestone Plan",
            "Dependency Map",
            "Critical Path Assumptions",
            "Resource Allocation",
            "Delay Monitoring Plan",
            "Gantt Chart Table",
        ],
        "template": """Create a professional Gantt chart planning prompt and schedule blueprint.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

Project Start Date: {project_start_date}
Project End Date: {project_end_date}
Major Phases: {major_phases}
Key Milestones: {key_milestones}
Resource Constraints: {resource_constraints}
Dependency Notes: {dependency_notes}

Build a realistic schedule plan with phases, dependencies, owners, and monitoring controls.

Provide:
{output_sections}

Include this table:
Task | Phase | Start Date | End Date | Duration | Dependency | Owner | Status""",
    },
    {
        "name": "Social Media Auto Posting Planner",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("Brand Name", "brand_name"),
            field("Target Audience", "target_audience", "text_area"),
            field("Platforms", "platforms", "multiselect", ["LinkedIn", "Instagram", "Facebook", "X / Twitter", "TikTok", "YouTube Shorts"]),
            field("Posting Frequency", "posting_frequency", "selectbox", ["Daily", "3 times per week", "Weekly", "Fortnightly", "Monthly"]),
            field("Content Pillars", "content_pillars", "text_area"),
            field("Tone", "tone", "selectbox", ["Professional", "Educational", "Friendly", "Sales-oriented", "Thought Leadership", "Luxury / Premium", "Technical"]),
            field("Approval Requirement", "approval_requirement"),
            field("Asset Source", "asset_source", "selectbox", ["Original photos", "AI-generated images", "Licensed stock images", "User-provided assets", "No images"]),
        ],
        "output_sections": [
            "Platform Strategy",
            "30-Day Content Calendar",
            "Post Ideas",
            "Captions",
            "Hashtags",
            "Image / Video Asset Suggestions",
            "Approval Workflow",
            "Copyright-Safe Content Rules",
            "Scheduling Workflow",
        ],
        "template": """Create a social media scheduling and approval automation plan.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

Brand Name: {brand_name}
Target Audience: {target_audience}
Platforms: {platforms}
Posting Frequency: {posting_frequency}
Content Pillars: {content_pillars}
Tone: {tone}
Approval Requirement: {approval_requirement}
Asset Source: {asset_source}

Create a practical content planning workflow for human-reviewed scheduling. Do not create instructions to auto-publish without review.

Provide:
{output_sections}

Include this table:
Date | Platform | Topic | Caption | Asset Suggestion | Hashtags | Status

Safety rules:
- Do not use copyrighted images without permission
- Do not use brand logos unless authorised
- Prefer original, AI-generated, licensed, or user-provided assets
- Human approval required before publishing
- Do not auto-publish without review""",
    },
    {
        "name": "Market Research Automation",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("Target Market", "target_market"),
            field("Competitors", "competitors", "text_area"),
            field("Research Frequency", "research_frequency", "selectbox", ["Weekly", "Monthly", "Quarterly"]),
            field(
                "Data Sources",
                "data_sources",
                "multiselect",
                ["Company Websites", "Google Search", "LinkedIn", "Industry Reports", "Government Data", "News", "Customer Reviews", "Social Media", "Internal Sales Data"],
            ),
            field("KPIs to Track", "kpis_to_track", "text_area"),
            field("Report Audience", "report_audience"),
        ],
        "output_sections": [
            "Market Research Automation Workflow",
            "Competitor Tracking System",
            "Trend Monitoring System",
            "Source List",
            "KPI Dashboard Plan",
            "Alert Rules",
            "Reporting Schedule",
            "Monthly Report Template",
        ],
        "template": """Create a market research automation workflow and reporting system.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

Target Market: {target_market}
Competitors: {competitors}
Research Frequency: {research_frequency}
Data Sources: {data_sources}
KPIs to Track: {kpis_to_track}
Report Audience: {report_audience}

Design a repeatable research process for monitoring competitors, market trends, and KPIs using approved sources and human review.

Provide:
{output_sections}

Include this table:
Data Source | What to Track | Frequency | Tool | Output""",
    },
    {
        "name": "Repetitive Task Automation",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("Repetitive Task Name", "repetitive_task_name"),
            field("Manual Steps", "manual_steps", "text_area"),
            field("Frequency", "frequency", "selectbox", ["Multiple times per day", "Daily", "Weekly", "Monthly"]),
            field("Time Spent", "time_spent"),
            field("Error Risks", "error_risks", "text_area"),
            field("Desired Outcome", "desired_outcome", "text_area"),
        ],
        "output_sections": [
            "Task Mapping",
            "Manual Step Analysis",
            "Automation Opportunities",
            "Trigger / Action Workflow",
            "Tool Recommendation",
            "SOP",
            "Risk Controls",
            "Time Saving Estimate",
        ],
        "template": """Create a repetitive task automation blueprint.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

Repetitive Task Name: {repetitive_task_name}
Manual Steps: {manual_steps}
Frequency: {frequency}
Time Spent: {time_spent}
Error Risks: {error_risks}
Desired Outcome: {desired_outcome}

Map the manual task, identify automation opportunities, and create a practical SOP with controls.

Provide:
{output_sections}

Include this table:
Manual Step | Automation Opportunity | Trigger | Action | Tool | Risk Control""",
    },
    {
        "name": "Data Analysis & Visualization",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("Data Source", "data_source"),
            field("Data Format", "data_format", "selectbox", ["CSV", "Excel", "Google Sheets", "SQL Database", "API", "Manual Entry"]),
            field("Metrics / KPIs", "metrics_kpis", "text_area"),
            field("Audience", "audience"),
            field("Dashboard Tool", "dashboard_tool", "selectbox", ["Excel", "Google Sheets", "Power BI", "Tableau", "Looker Studio", "Streamlit", "Python"]),
            field("Chart Types", "chart_types", "multiselect", ["Bar Chart", "Line Chart", "Pie Chart", "Scatter Plot", "Heatmap", "Gantt Chart", "KPI Cards", "Dashboard", "Funnel Chart"]),
            field("Reporting Frequency", "reporting_frequency"),
        ],
        "output_sections": [
            "Data Pipeline",
            "Data Cleaning Steps",
            "KPI Definitions",
            "Dashboard Layout",
            "Recommended Charts",
            "Automated Reporting Schedule",
            "Data Quality Checks",
            "Executive Insight Summary",
        ],
        "template": """Create a data analysis and visualization automation plan.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

Data Source: {data_source}
Data Format: {data_format}
Metrics / KPIs: {metrics_kpis}
Audience: {audience}
Dashboard Tool: {dashboard_tool}
Chart Types: {chart_types}
Reporting Frequency: {reporting_frequency}

Design a practical analytics workflow with clean data inputs, KPI logic, visualization choices, and reporting cadence.

Provide:
{output_sections}

Include this table:
KPI | Data Source | Calculation | Chart Type | Update Frequency""",
    },
    {
        "name": "Office Automation",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("Department", "department", "selectbox", ["Admin", "Sales", "Operations", "Construction", "Finance", "HR", "Marketing", "Customer Service"]),
            field("Admin Tasks", "admin_tasks", "text_area"),
            field("Documents Used", "documents_used", "text_area"),
            field("Approval Process", "approval_process", "text_area"),
            field("Communication Channels", "communication_channels"),
            field("Bottlenecks", "bottlenecks", "text_area"),
        ],
        "output_sections": [
            "Office Workflow Assessment",
            "Document Template System",
            "Email Automation Plan",
            "Calendar Automation Plan",
            "Approval Workflow",
            "Filing System",
            "Reporting Routine",
            "SOP",
        ],
        "template": """Create an office automation plan for a department workflow.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

Department: {department}
Admin Tasks: {admin_tasks}
Documents Used: {documents_used}
Approval Process: {approval_process}
Communication Channels: {communication_channels}
Bottlenecks: {bottlenecks}

Design a practical office workflow with templates, approvals, filing, communication, and reporting routines.

Provide:
{output_sections}

Include this table:
Office Task | Current Process | Automation Method | Tool | Owner | Frequency""",
    },
    {
        "name": "File Organization Automation",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("File Types", "file_types", "text_area"),
            field("Current Folder Structure", "current_folder_structure", "text_area"),
            field("Naming Problems", "naming_problems", "text_area"),
            field("Storage Platform", "storage_platform", "selectbox", ["Google Drive", "OneDrive", "Dropbox", "Local Server", "SharePoint", "Other"]),
            field("Access Rules", "access_rules", "text_area"),
            field("Retention Requirements", "retention_requirements", "text_area"),
        ],
        "output_sections": [
            "Folder Structure",
            "Naming Convention",
            "Auto-Tagging Rules",
            "File Routing Workflow",
            "Backup Process",
            "Version Control Rules",
            "Archive Policy",
            "Access Permission Matrix",
        ],
        "template": """Create a file organization automation blueprint.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

File Types: {file_types}
Current Folder Structure: {current_folder_structure}
Naming Problems: {naming_problems}
Storage Platform: {storage_platform}
Access Rules: {access_rules}
Retention Requirements: {retention_requirements}

Design a controlled filing, naming, access, backup, and retention system that can be implemented with the selected storage platform.

Provide:
{output_sections}

Include this table:
File Type | Folder Path | Naming Rule | Owner | Retention Period | Access Level""",
    },
    {
        "name": "Promotion Email Automation",
        "fields": [
            *AUTOMATION_COMMON_FIELDS,
            field("Campaign Name", "campaign_name"),
            field("Product / Service", "product_service"),
            field("Target Audience", "target_audience", "text_area"),
            field("Offer", "offer", "text_area"),
            field("Email Sequence Length", "email_sequence_length", "selectbox", ["3 emails", "5 emails", "7 emails"]),
            field("Tone", "tone"),
            field("CTA", "cta"),
            field("Compliance Region", "compliance_region", "selectbox", ["Australia", "United States", "United Kingdom", "European Union", "Other"]),
        ],
        "output_sections": [
            "Campaign Strategy",
            "Audience Segments",
            "Email Sequence",
            "Subject Lines",
            "Email Body Drafts",
            "CTA Recommendations",
            "Follow-up Schedule",
            "Compliance Checklist",
            "Performance Metrics",
        ],
        "template": """Create a promotion email automation campaign plan.

Business / Project Name: {business_project_name}
Industry: {industry}
Goal: {goal}
Current Process: {current_process}
Tools Used: {tools_used}
Preferred Output Format: {output_format}

Campaign Name: {campaign_name}
Product / Service: {product_service}
Target Audience: {target_audience}
Offer: {offer}
Email Sequence Length: {email_sequence_length}
Tone: {tone}
CTA: {cta}
Compliance Region: {compliance_region}

Create a compliant, human-reviewed email campaign plan. Do not send emails, scrape contacts, or use purchased lists.

Provide:
{output_sections}

Include this table:
Email # | Timing | Subject Line | Goal | CTA | Follow-up Condition

Compliance reminders:
- Include unsubscribe option
- Avoid misleading subject lines
- Respect consent and privacy
- Do not scrape or use purchased emails without permission
- Follow applicable spam and privacy laws""",
    },
]


def run_fast_mode(query: str) -> dict:
    # Both modes use the same authorization, evidence, budgets and saved report.
    return run_advanced_mode(query)


def run_advanced_mode(query: str) -> dict:
    import uuid
    project=get_active_project()
    signature=(get_current_user_id(),project["id"],query.strip())
    pending=st.session_state.get("pending_analysis_request")
    if not pending or pending["signature"]!=signature:
        pending={"signature":signature,"id":uuid.uuid4().hex}
        st.session_state["pending_analysis_request"]=pending
    from analysis_service import analyze, AnalysisBusy
    try:
        result=analyze(get_current_user_id(),project["id"],query,pending["id"])
    except AnalysisBusy as exc:
        raise requests.exceptions.RequestException(str(exc)) from None
    except Exception:
        st.session_state.pop('pending_analysis_request',None)
        raise requests.exceptions.RequestException('Analysis could not complete. Check project context, account budget, and service availability before retrying.') from None
    st.session_state.pop('pending_analysis_request',None)
    return result


def run_copilot_request(user_input: str, user_id: str = "default") -> str:
    if not os.getenv("OPENAI_API_KEY"):
        try:
            import config

            config.load_environment()
        except Exception:
            pass

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    try:
        project = get_active_project()
        if project is None:
            raise PermissionError("Select an authorized project first.")
        return run_engine(user_id, user_input, project_id=project["id"])
    except Exception as exc:
        raise RuntimeError("AI Copilot request failed.") from exc


def save_history_entry(
    query: str,
    mode_name: str,
    payload: dict,
    elapsed_seconds: float,
    metadata: dict | None = None,
) -> dict:
    if payload.get("status") == "context_required":
        st.warning(payload["result"])
        return payload
    if payload.get("id"):
        project=get_active_project()
        saved=report_store.get_report(get_current_user_id(),project["id"],payload["id"])
        if saved is None:raise PermissionError("Saved report is not available in this project.")
        st.session_state.selected_history=saved
        return saved
    entry = {
        "query": query,
        "mode": mode_name,
        "category": payload.get("category", ""),
        "confidence": payload.get("confidence", ""),
        "version": payload.get("version", ""),
        "result": payload.get("result", ""),
        "elapsed_seconds": elapsed_seconds,
    }
    if metadata:
        entry.update(metadata)
    if payload.get("agent_mode"):
        entry["agent_mode"] = payload["agent_mode"]
    for key in ("sources", "status"):
        if key in payload:
            entry[key] = payload[key]
    project = get_active_project()
    if project is None:
        raise PermissionError("Select an authorized project before saving a report.")
    entry = report_store.save_report(get_current_user_id(), project["id"], entry)
    st.session_state.history.insert(0, entry)
    st.session_state.history = st.session_state.history[:HISTORY_LIMIT]
    st.session_state.selected_history = entry
    return entry


def get_document_analysis_type(query: str) -> str | None:
    for line in query.splitlines():
        if line.startswith("Analysis Type:"):
            analysis_type = line.split(":", 1)[1].strip()
            if analysis_type in DOCUMENT_PDF_FILENAMES:
                return analysis_type
    return None


def get_project_review_type(query: str) -> str | None:
    for line in query.splitlines():
        if line.startswith("Review Type:"):
            review_type = line.split(":", 1)[1].strip()
            if review_type in PROJECT_REVIEW_PDF_FILENAMES:
                return review_type
    return None


def build_pdf_report(
    analysis_type: str,
    report_content: str,
    agent_mode: str | None = None,
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    generated_time = time.strftime("%Y-%m-%d %H:%M:%S")
    buffer = BytesIO()
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=base_styles["Title"],
        fontName="STSong-Light",
        fontSize=18,
        leading=24,
        spaceAfter=12,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=base_styles["Normal"],
        fontName="STSong-Light",
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    content_style = ParagraphStyle(
        "ReportContent",
        parent=base_styles["Normal"],
        fontName="STSong-Light",
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=base_styles["Heading2"],
        fontName="STSong-Light",
        fontSize=12,
        leading=16,
        spaceBefore=8,
        spaceAfter=6,
    )

    story = [
        Paragraph("Gao Intelligence Hub", title_style),
        Paragraph(f"Analysis Type: {escape(analysis_type)}", meta_style),
        Paragraph(f"Generated Time: {escape(generated_time)}", meta_style),
    ]
    if agent_mode:
        story.append(Paragraph(f"Agent Mode: {escape(agent_mode)}", meta_style))
    story.extend([Spacer(1, 8), Paragraph("Report Content", heading_style)])

    for line in report_content.splitlines():
        if line.strip():
            story.append(Paragraph(escape(line), content_style))
        else:
            story.append(Spacer(1, 6))

    document.build(story)
    return buffer.getvalue()


def render_pdf_download(entry: dict) -> None:
    analysis_type = get_document_analysis_type(entry.get("query", ""))
    review_type = get_project_review_type(entry.get("query", ""))
    report_content = str(entry.get("result", ""))
    report_type = analysis_type or review_type or str(entry.get("mode") or "Analysis Report")
    if not report_content:
        return

    pdf_bytes = build_pdf_report(
        report_type,
        report_content,
        entry.get("agent_mode"),
    )
    file_name = DOCUMENT_PDF_FILENAMES.get(
        report_type,
        PROJECT_REVIEW_PDF_FILENAMES.get(report_type, "analysis_report.pdf"),
    )
    st.download_button(
        "Download Report PDF",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
        use_container_width=True,
    )


def inject_custom_css() -> None:
    from ui_theme import inject
    inject()


def render_hero() -> None:
    st.markdown(
        """
        <div class="hub-hero">
            <h1>Gao Intelligence Hub</h1>
            <h2 class="hero-subtitle">Business, Construction &amp; Executive AI Intelligence Platform</h2>
            <p>Transform project documents, business data, and executive workflows into decision-ready intelligence.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mobile_guide() -> None:
    steps = [
        (
            "1",
            "Open the sidebar",
            "Tap the arrow/menu on the left to access tools.",
        ),
        (
            "2",
            "Choose a tool",
            "Use Prompt Library, Form Builder, Document Intelligence, Automation Intelligence, or Executive Intelligence.",
        ),
        (
            "3",
            "Generate your request",
            "Load a template or generate a professional prompt.",
        ),
        (
            "4",
            "Submit and download",
            "Run the analysis, then download the PDF report.",
        ),
    ]
    with st.expander("📱 Mobile Quick Guide", expanded=False):
        for step_number, title, text in steps:
            st.markdown(
                f"""
                <div class="mobile-guide-wrapper">
                    <div class="mobile-guide-card">
                        <div class="mobile-guide-title">
                            <span class="mobile-guide-step">{step_number}.</span> {title}
                        </div>
                        <div class="mobile-guide-text">{text}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_status_cards() -> None:
    cards = [
        {
            "icon": "🔬",
            "title": "Business Intelligence",
            "description": "Market, sales, financial, and operating intelligence.",
        },
        {
            "icon": "🏗️",
            "title": "Construction Intelligence",
            "description": "Project, contract, compliance, and delivery analysis.",
        },
        {
            "icon": "📄",
            "title": "Document Intelligence",
            "description": "Extract and analyze PDF, DOCX, XLSX, and TXT files.",
        },
        {
            "icon": "🧠",
            "title": "Executive Decision Support",
            "description": "Board-ready reports powered by executive agent modes.",
        },
    ]
    card_markup = "\n".join(
        f"""
        <div class="status-card-native card">
            <div class="status-card-top">
                <div class="status-card-icon">{card["icon"]}</div>
                <div class="status-card-badge">Active</div>
            </div>
            <div class="status-card-title">{escape(card["title"])}</div>
            <div class="status-card-description">{escape(card["description"])}</div>
        </div>
        """
        for card in cards
    )
    st.markdown(f'<div class="grid status-card-grid">{card_markup}</div>', unsafe_allow_html=True)


def render_mobile_navigation_tabs() -> None:
    st.markdown(
        """
        <div class="hub-mobile-tabs">
            <div class="tab-row">
                <div class="tab-pill">Prompt Library</div>
                <div class="tab-pill">Form Builder</div>
                <div class="tab-pill">Document Analysis</div>
                <div class="tab-pill">Executive Intelligence</div>
                <div class="tab-pill">Automation Intelligence</div>
                <div class="tab-pill">History</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def initialize_auth_state() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = st.session_state.authenticated
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid4())
    if "username" not in st.session_state:
        st.session_state.username = None
    if "role" not in st.session_state:
        st.session_state.role = None


def set_guest_user() -> None:
    guest_user = dict(GUEST_USER)
    st.session_state.authenticated = False
    st.session_state.is_logged_in = False
    st.session_state["user"] = guest_user
    st.session_state.current_user = guest_user
    st.session_state.user_id = guest_user["id"]
    st.session_state.username = guest_user["username"]
    st.session_state.role = guest_user["role"]


def ensure_guest_user() -> None:
    if st.session_state.get("is_logged_in"):
        return
    if st.session_state.get("user", {}).get("id") != GUEST_USER["id"]:
        set_guest_user()
    st.session_state.active_project_id = None


def is_guest_user() -> bool:
    return st.session_state.get("user", {}).get("id") == GUEST_USER["id"]


def set_authenticated_user(user: dict, reset_navigation: bool = True) -> None:
    st.session_state.pop("auth_modal_open", None)
    st.session_state.authenticated = True
    st.session_state.is_logged_in = True
    st.session_state["user"] = user
    st.session_state.current_user = user
    st.session_state.user_id = str(user["id"])
    st.session_state.username = user["username"]
    st.session_state.role = user["role"]
    if reset_navigation:
        st.session_state["active_section"] = DEFAULT_SECTION
        st.session_state.active_project_id = None


def clear_authenticated_user() -> None:
    set_guest_user()
    st.session_state.active_project_id = None
    st.session_state.selected_history = None
    st.session_state.history = []
    st.session_state.copilot_history = []
    st.session_state.query = ""


def initialize_cookie_manager() -> EncryptedCookieManager:
    cookies = EncryptedCookieManager(
        prefix=COOKIE_PREFIX,
        password=get_cookie_secret(),
    )
    return cookies


def get_cookie_secret() -> str:
    import secrets
    from pathlib import Path
    configured = os.getenv("COOKIE_SECRET_KEY") or os.getenv("COOKIE_PASSWORD")
    if configured and configured not in {"a-very-secret-key", "change-me-cookie-secret"}:
        return configured
    secret_file = Path(__file__).with_name(".cookie_secret")
    import tempfile
    if secret_file.exists():
        return secret_file.read_text().strip()
    with tempfile.NamedTemporaryFile(mode="w", dir=secret_file.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(secrets.token_urlsafe(48))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        try:
            os.link(temporary, secret_file)
        except FileExistsError:
            pass
        return secret_file.read_text().strip()
    finally:
        temporary.unlink(missing_ok=True)


def cookie_manager_ready(cookies: EncryptedCookieManager) -> bool:
    """Test jars have no browser handshake; real managers must report readiness."""
    ready = getattr(cookies, "ready", None)
    return bool(ready()) if ready is not None else True


def restore_authenticated_user_from_cookie(cookies: EncryptedCookieManager) -> None:
    if not cookie_manager_ready(cookies):
        if st.session_state.get("is_logged_in"):
            clear_authenticated_user()
        return
    token = cookies.get(COOKIE_SESSION_KEY)
    user = user_store.resolve_session(token) if token else None
    if user is None:
        if st.session_state.get("is_logged_in"):
            clear_authenticated_user()
        return
    st.session_state["auth_session_token"] = token
    set_authenticated_user(user, reset_navigation=False)


def persist_authenticated_user(cookies: EncryptedCookieManager, user: dict) -> None:
    token = user_store.create_session(user["id"])
    cookies[COOKIE_SESSION_KEY] = token
    cookies[COOKIE_USER_ID_KEY] = ""
    st.session_state["auth_session_token"] = token
    cookies.save()


def clear_authentication_cookie(cookies: EncryptedCookieManager) -> None:
    user_store.revoke_session(cookies.get(COOKIE_SESSION_KEY))
    cookies[COOKIE_SESSION_KEY] = ""
    cookies[COOKIE_USER_ID_KEY] = ""
    st.session_state.pop("auth_session_token", None)
    cookies.save()


def render_auth_page(cookies: EncryptedCookieManager) -> None:
    render_home_logo()
    if st.button("Close sign-in", key="close_auth_modal"):
        st.session_state.pop("auth_modal_open", None)
        st.session_state["active_section"] = DEFAULT_SECTION
        st.rerun()
    gate_message = st.session_state.pop("auth_gate_message", "")
    st.markdown(
        """
        <div class="auth-container">
            <div class="auth-box">
                <h2>Gao Intelligence Hub</h2>
                <p>Sign in to unlock project storage, document intelligence, reports, and premium Construction AI workflows.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if gate_message:
        st.info(gate_message)

    if not cookie_manager_ready(cookies):
        st.warning("Secure sign-in is waiting for the browser cookie component. Reload this page or try another browser. The public sample workspace remains available using Close sign-in.")
        return

    sign_in_tab, create_account_tab, recovery_tab = st.tabs(["Sign In", "Create Account", "Forgot password?"])

    with sign_in_tab:
        with st.form("sign_in_form"):
            email = st.text_input("Username or Email", key="auth_sign_in_identifier")
            password = st.text_input("Password", type="password", key="auth_sign_in_password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

        if submitted:
            try:
                from account_ui import source_id
                user = user_store.authenticate_user(email, password,source=source_id())
            except user_store.UserStoreError:
                st.error("Could not sign in right now. Please try again later.")
            else:
                if user is None:
                    st.error("Invalid email or password.")
                else:
                    set_authenticated_user(user)
                    persist_authenticated_user(cookies, user)
                    st.rerun()

    with create_account_tab:
        with st.form("create_account_form"):
            username = st.text_input("Name", key="auth_create_username")
            email = st.text_input("Email", key="auth_create_email")
            password = st.text_input("Password", type="password", key="auth_create_password")
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="auth_create_confirm_password",
            )
            submitted = st.form_submit_button("Register", type="primary", use_container_width=True)

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    from account_ui import source_id
                    import account_security,account_recovery
                    with user_store.get_connection() as auth_connection:
                        auth_connection.execute('BEGIN IMMEDIATE')
                        if not account_security.allowed(auth_connection,'signup',source_id(),source_id(),account_limit=5,source_limit=5):
                            raise ValueError('Too many registration attempts. Try again in 15 minutes.')
                    if not account_recovery.delivery_ready():raise ValueError('Account activation email is temporarily unavailable. Please try later.')
                    user = user_store.create_user(username, email, password,require_verification=True)
                    account_recovery.request_code(email,source=source_id(),purpose='activate')
                except ValueError as exc:
                    st.error(str(exc))
                except user_store.UserStoreError:
                    st.error("Could not create account right now. Please try again later.")
                else:
                    st.success('Account created. Enter the email activation code below, then sign in.')

        from account_ui import render_activation
        render_activation()

    with recovery_tab:
        from account_ui import render_recovery
        render_recovery()


def show_login_modal(message: str = "Sign in to continue.") -> None:
    st.session_state["auth_modal_open"] = True
    st.session_state["auth_gate_message"] = message
    st.rerun()


def show_upgrade_modal() -> None:
    show_login_modal("Upgrade to unlock full Construction AI capabilities.")


def require_authenticated_user(message: str = "Sign in to unlock this workspace.") -> bool:
    if not is_guest_user():
        return True
    show_login_modal(message)
    st.stop()
    return False


def require_premium_access() -> bool:
    if is_guest_user():
        show_upgrade_modal()
        st.stop()
        return False
    return True


def render_home_logo() -> None:
    if st.button("Gao Intelligence", key="brand_home", help="Back to Home", use_container_width=True):
        st.session_state.pop("auth_modal_open", None)
        set_active_section(DEFAULT_SECTION)
        st.rerun()


def render_auth_header(cookies: EncryptedCookieManager) -> None:
    with st.container(key="app_header"):
        columns=st.columns([3,2,1,1] if is_guest_user() else [3,2,1])
        with columns[0]:render_home_logo()
        with columns[1]:
            username="Guest preview" if is_guest_user() else str(st.session_state.username or "Account")
            st.markdown('<div class="auth-action-shell"><span class="auth-avatar">'+escape(username)+'</span></div>',unsafe_allow_html=True)
        if is_guest_user():
            with columns[2]:
                if st.button("Login",key="top_login",use_container_width=True):show_login_modal("Sign in to your private workspace.")
            with columns[3]:
                if st.button("Sign Up",key="top_signup",type="primary",use_container_width=True):show_login_modal("Create an account to save projects and reports.")
        else:
            with columns[2]:
                if st.button("Sign Out",key="top_sign_out",use_container_width=True):
                    clear_authentication_cookie(cookies);clear_authenticated_user();st.rerun()
    with st.container(key="quick_navigation"):
        for column,section in zip(st.columns(6),NAVIGATION_OPTIONS):
            with column:
                st.button("Home" if section==DEFAULT_SECTION else section,key="quick_nav_"+section,use_container_width=True,type="primary" if st.session_state.get('active_section')==section else "secondary",on_click=set_active_section,args=(section,))


def get_current_user_id() -> int:
    if is_guest_user():
        raise PermissionError("Guest users do not have a persisted account.")
    if st.session_state.user_id is not None:
        return int(st.session_state.user_id)
    current_user = st.session_state.current_user or {}
    return int(current_user["id"])


def format_limit(limit: int | None) -> str:
    if limit is None:
        return "Unlimited"
    return str(limit)


def format_renewal_date(value: str | None) -> str:
    parsed_value = subscription_store.parse_datetime(value)
    if parsed_value is None:
        return "Not set"
    return parsed_value.date().isoformat()


def refresh_subscription_usage() -> dict:
    if is_guest_user():
        return {
            "events": [],
            "subscription_tier": "Guest Preview",
            "current_request_count": st.session_state.get("guest_copilot_calls", 0),
            "monthly_request_limit": GUEST_COPILOT_SESSION_LIMIT,
            "current_document_count": 0,
            "monthly_document_limit": 0,
            "subscription_end": None,
        }
    usage = subscription_store.load_usage(get_current_user_id())
    if st.session_state.current_user is not None:
        st.session_state.current_user.update(usage)
    return usage


def save_usage(user_id: int, docs: int = 0, api_calls: int = 0) -> dict:
    return subscription_store.save_usage(user_id, docs, api_calls)


def load_usage(user_id: int) -> dict:
    return subscription_store.load_usage(user_id)


def build_usage_trend(usage: dict) -> dict[str, list[int]]:
    today = subscription_store.utc_now().date()
    days = [today - timedelta(days=offset) for offset in range(4, -1, -1)]
    documents = {day: 0 for day in days}
    api_requests = {day: 0 for day in days}

    for event in usage.get("events", []):
        created_at = subscription_store.parse_datetime(event.get("created_at"))
        if created_at is None:
            continue
        event_day = created_at.date()
        if event_day not in documents:
            continue
        amount = int(event.get("amount") or 0)
        if event.get("event_type") == "documents":
            documents[event_day] += amount
        elif event.get("event_type") == "api_requests":
            api_requests[event_day] += amount

    if not any(documents.values()) and int(usage.get("current_document_count") or 0):
        documents[today] = int(usage.get("current_document_count") or 0)
    if not any(api_requests.values()) and int(usage.get("current_request_count") or 0):
        api_requests[today] = int(usage.get("current_request_count") or 0)

    return {
        "Documents": [documents[day] for day in days],
        "API Requests": [api_requests[day] for day in days],
    }


def build_agent_usage_chart() -> dict[str, list[int]]:
    agent_counts = {
        "Legal": 0,
        "Finance": 0,
        "Risk": 0,
    }
    for entry in st.session_state.history:
        query = f'{entry.get("query", "")} {entry.get("category", "")}'.lower()
        if any(term in query for term in ("legal", "contract", "clause", "tender")):
            agent_counts["Legal"] += 1
        if any(term in query for term in ("finance", "payment", "cost", "budget")):
            agent_counts["Finance"] += 1
        if any(term in query for term in ("risk", "safety", "compliance", "delay")):
            agent_counts["Risk"] += 1

    return {agent: [count] for agent, count in agent_counts.items()}


def consume_ai_request_or_warn() -> bool:
    if is_guest_user():
        show_login_modal("Sign in to run advanced AI analysis and save your work.")
        st.stop()
        return False
    can_use, message = subscription_store.can_use_ai_request(get_current_user_id())
    if not can_use:
        st.error(message)
        return False
    try:
        subscription_store.increment_ai_request(get_current_user_id())
    except PermissionError as exc:
        st.error(str(exc))
        return False
    refresh_subscription_usage()
    return True


def enforce_copilot_rate_limit() -> None:
    if "copilot_calls" not in st.session_state:
        st.session_state.copilot_calls = 0

    if st.session_state.copilot_calls > COPILOT_SESSION_CALL_LIMIT:
        st.error("Usage limit reached. Upgrade required.")
        st.stop()


def consume_document_analysis_or_warn() -> bool:
    if is_guest_user():
        show_login_modal("Sign in to upload documents and generate document intelligence.")
        st.stop()
        return False
    can_use, message = subscription_store.can_use_document_analysis(get_current_user_id())
    if not can_use:
        st.error(message)
        return False
    try:
        subscription_store.increment_document_analysis(get_current_user_id())
    except PermissionError as exc:
        st.error(str(exc))
        return False
    refresh_subscription_usage()
    return True


def consume_executive_agent_usage_or_warn() -> bool:
    if is_guest_user():
        show_upgrade_modal()
        st.stop()
        return False
    can_use_documents, document_message = subscription_store.can_use_document_analysis(get_current_user_id())
    if not can_use_documents:
        st.error(document_message)
        return False

    can_use_ai, ai_message = subscription_store.can_use_ai_request(get_current_user_id())
    if not can_use_ai:
        st.error(ai_message)
        return False

    try:
        subscription_store.increment_document_analysis(get_current_user_id())
        subscription_store.increment_ai_request(get_current_user_id())
    except PermissionError as exc:
        st.error(str(exc))
        return False

    refresh_subscription_usage()
    return True


def render_subscription_summary() -> None:
    try:
        usage = refresh_subscription_usage()
    except ValueError:
        st.error("Could not load subscription details.")
        return

    request_usage = f'{usage["current_request_count"]} / {format_limit(usage["monthly_request_limit"])}'
    document_usage = f'{usage["current_document_count"]} / {format_limit(usage["monthly_document_limit"])}'
    renewal_date = format_renewal_date(usage["subscription_end"])

    st.markdown("#### Subscription")
    st.markdown(
        f"""
        <div class="subscription-desktop-metrics">
            <div class="subscription-desktop-metric">
                <div class="subscription-desktop-label">Plan</div>
                <div class="subscription-desktop-value">{escape(str(usage["subscription_tier"]))}</div>
            </div>
            <div class="subscription-desktop-metric">
                <div class="subscription-desktop-label">Usage</div>
                <div class="subscription-desktop-value">{escape(request_usage)}</div>
            </div>
            <div class="subscription-desktop-metric">
                <div class="subscription-desktop-label">Documents</div>
                <div class="subscription-desktop-value">{escape(document_usage)}</div>
            </div>
            <div class="subscription-desktop-metric">
                <div class="subscription-desktop-label">Renewal Date</div>
                <div class="subscription-desktop-value">{escape(renewal_date)}</div>
            </div>
        </div>
        <div class="subscription-mobile-card">
            <div class="subscription-mobile-title">{escape(str(usage["subscription_tier"]))}</div>
            <div class="subscription-mobile-line">{escape(request_usage)} Requests</div>
            <div class="subscription-mobile-line">{escape(document_usage)} Documents</div>
            <div class="subscription-mobile-renewal">Renews:<br><strong>{escape(renewal_date)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_user_limit_summary() -> None:
    try:
        active_users, max_users = user_store.get_user_limit_status()
    except user_store.UserStoreError:
        st.error("Could not load user count.")
        return

    max_users_label = "Unlimited" if max_users == 0 else str(max_users)
    st.caption(f"Users: {active_users} / {max_users_label}")


def render_page_header(title: str, subtitle: str = "") -> None:
    subtitle_markup = f'<p class="enterprise-subtitle">{escape(subtitle)}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="enterprise-page-header">
            <h1 class="enterprise-title">{escape(title)}</h1>
            {subtitle_markup}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="dashboard-metric-card">
            <div class="dashboard-metric-label">{escape(label)}</div>
            <div class="dashboard-metric-value">{escape(value)}</div>
            <div class="dashboard-metric-note">{escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_construction_hero(username: str) -> None:
    st.markdown('<section class="construction-hero"><div class="hero-kicker">Construction intelligence workspace</div><h1>Project intelligence.</h1><p class="hero-support">Review documents, check IFC models and turn project evidence into clear next steps.</p></section>',unsafe_allow_html=True)


def render_workspace_card(title: str, description: str, meta: str) -> None:
    st.markdown(
        f"""
        <div class="workspace-command-card">
            <div class="workspace-card-label">{escape(title)}</div>
            <div class="workspace-card-body">{escape(description)}</div>
            <div class="workspace-card-meta">{escape(meta)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace_cards(title: str, cards: list[tuple[str, str, str]]) -> None:
    st.markdown(f'<div class="workspace-section-title">{escape(title)}</div>', unsafe_allow_html=True)
    card_markup = "\n".join(
        (
            '<div class="workspace-command-card">'
            f'<div class="workspace-card-label">{escape(card_title)}</div>'
            f'<div class="workspace-card-body">{escape(description)}</div>'
            f'<div class="workspace-card-meta">{escape(meta)}</div>'
            "</div>"
        )
        for card_title, description, meta in cards
    )
    st.markdown(f'<div class="workspace-card-grid">{card_markup}</div>', unsafe_allow_html=True)
    if not is_guest_user():
        selected=st.selectbox('Choose workflow',[card[0] for card in cards],key='workflow_'+title)
        st.button('Open selected workflow',key='workflow_open_'+title,use_container_width=True,on_click=open_workspace_workflow,args=('workflow_'+title,))
    if is_guest_user():
        selected = st.selectbox("Choose a sample review", [card[0] for card in cards], key=f"sample_choice_{title}")
        if st.button("Open sample workflow", key=f"sample_open_{title}"):
            st.session_state["public_demo_workflow"] = "BIM Review" if selected=="BIM Model Checks" else selected
            set_active_section("Copilot")
            st.rerun()


def format_message_markdown(content: str) -> str:
    escaped_content = escape(content)
    parts = escaped_content.split("```")
    rendered_parts = []
    for index, part in enumerate(parts):
        if index % 2 == 1:
            rendered_parts.append(f"<pre><code>{part.strip()}</code></pre>")
        else:
            text = part.replace("\n", "<br>")
            text = text.replace("**", "")
            rendered_parts.append(text)
    return "".join(rendered_parts)


def format_citations(sources: list[str] | None) -> str:
    if not sources:
        return ""
    citation_markup = "".join(
        f'<span class="citation-pill">[{index}] {escape(source)}</span>'
        for index, source in enumerate(sources[:4], start=1)
    )
    return f'<div class="citation-row">{citation_markup}</div>'


def source_labels_from_retrieval(retrieved_chunks: list[dict]) -> list[str]:
    return [format_sources([chunk]).removeprefix("[1] ") for chunk in retrieved_chunks[:4]]


def format_chat_bubble(role: str, content: str) -> str:
    row_class = "chat-user" if role == "user" else "chat-assistant"
    bubble_class = "user-msg" if role == "user" else "ai-msg"
    rendered_content = escape(content) if role == "user" else format_message_markdown(content)
    # Keep generated HTML on one line: indented blocks inside the history
    # wrapper are otherwise interpreted as Markdown code blocks.
    return (
        f'<div class="chat-row {row_class}">'
        f'<div class="chat-bubble {bubble_class}">{rendered_content}</div>'
        '</div>'
    )


def render_chat_bubble(role: str, content: str) -> None:
    st.markdown(
        format_chat_bubble(role, content),
        unsafe_allow_html=True,
    )


def render_typing_indicator() -> None:
    st.markdown(
        """
        <div class="chat-container">
            <div class="chat-row chat-assistant">
                <div class="typing-indicator" aria-label="Assistant is analyzing">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span>Analyzing project context</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report_section(title: str, content: str) -> None:
    st.markdown(
        f"""
        <section class="report-section">
            <h3>{escape(title)}</h3>
            <div>{escape(content).replace(chr(10), "<br>")}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def responsive_columns(count: int):
    """Return Streamlit columns styled by CSS to collapse cleanly on mobile."""
    return st.columns(count, gap="medium")


def normalize_section(section: str | None) -> str:
    normalized = SECTION_ALIASES.get(section or "", section or DEFAULT_SECTION)
    if normalized not in NAVIGATION_OPTIONS:
        return DEFAULT_SECTION
    return normalized


def set_active_section(section: str, documents_view: str | None = None) -> str:
    normalized_section = normalize_section(section)
    st.session_state["active_section"] = normalized_section
    if documents_view is not None:
        st.session_state.documents_view = documents_view
    return normalized_section


def open_workspace_workflow(key):
    selected=st.session_state.get(key,'NCC Compliance')
    if selected=='BIM Model Checks':set_active_section('BIM')
    else:
        st.session_state['copilot_draft']='Prepare a '+selected.lower()+' review for this project. Use the project evidence, identify gaps and cite relevant sources.'
        set_active_section('Copilot')


def change_workspace_project(key):
    # Browser widget events can arrive after sign-out or session revocation.
    # Never use a cached private identity to process such an event.
    session_user=user_store.resolve_session(st.session_state.get('auth_session_token'))
    if is_guest_user() or not session_user or str(session_user['id'])!=str(st.session_state.get('user_id')):
        clear_authenticated_user()
        st.session_state.pop('auth_session_token',None)
        sync_project_session()
        return
    selected=st.session_state.get(key)
    try:
        if selected is not None:project_store.require_project_access(get_current_user_id(),selected)
    except PermissionError:
        st.session_state.active_project_id=None
        sync_project_session()
        return
    st.session_state.active_project_id=selected
    sync_project_session()


def sync_navigation_selection() -> None:
    # Widget callbacks run before the next script pass, so manual selection
    # reaches active_section before the widget is synchronized below.
    set_active_section(st.session_state["nav_selected"])


def get_active_project() -> dict | None:
    if is_guest_user():
        return None
    active_project_id = st.session_state.get("active_project_id")
    if active_project_id is None:
        return None
    try:
        return project_store.get_project(int(active_project_id), get_current_user_id())
    except (ValueError, project_store.ProjectStoreError):
        return None


def require_active_project() -> bool:
    if is_guest_user():
        show_login_modal("Sign in to create projects and unlock full Construction AI workflows.")
        st.stop()
        return False
    if get_active_project() is None:
        st.warning("Please create or select a project first.")
        return False
    return True


def add_active_project_history(action_type: str, content: str) -> None:
    if is_guest_user():
        return
    active_project = get_active_project()
    if active_project is None:
        return
    try:
        project_store.add_project_history(active_project["id"], action_type, content, user_id=get_current_user_id())
    except (ValueError, project_store.ProjectStoreError):
        st.warning("Project history could not be saved.")


def sync_project_session() -> None:
    project = get_active_project()
    scope = (str(st.session_state.get("user_id")), project["id"] if project else None)
    if st.session_state.get("loaded_project_scope") != scope:
        st.session_state.history = []
        st.session_state.selected_history = None
        st.session_state.copilot_history = []
        st.session_state.query = ""
        for key in ("copilot_pending_prompt", "copilot_draft", "report_search", "reports_selected", "upload_page_documents", "document_analysis_upload", "project_review_upload"):
            st.session_state.pop(key, None)
        st.session_state.loaded_project_scope = scope
    if project:
        st.session_state.history = report_store.list_reports(get_current_user_id(), project["id"])


def render_new_project_form() -> None:
    if is_guest_user():
        st.markdown(
            """
            <div class="guest-banner">
                Create an account to save projects, upload documents, and keep a persistent construction intelligence timeline.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign in to create projects", key="guest_project_gate", use_container_width=True):
            show_login_modal("Sign in or create an account to start a project workspace.")
            st.stop()
        return

    with st.expander("New Project", expanded=False):
        with st.form("new_project_form"):
            project_name = st.text_input("Project Name", key="new_project_name")
            project_description = st.text_area("Description", key="new_project_description", height=90)
            submitted = st.form_submit_button("Create Project", type="primary", use_container_width=True)

        if submitted:
            try:
                project = project_store.create_project(
                    get_current_user_id(),
                    project_name,
                    project_description,
                )
            except ValueError as exc:
                st.error(str(exc))
            except project_store.ProjectStoreError:
                st.error("Could not create project right now.")
            else:
                st.session_state.active_project_id = project["id"]
                set_active_section(DEFAULT_SECTION)
                st.rerun()


def render_projects_list(title: str = "Recent Projects") -> None:
    st.markdown(f'<div class="workspace-section-title">{escape(title)}</div>', unsafe_allow_html=True)
    if is_guest_user():
        st.caption("Project history is available after sign in.")
        return
    try:
        projects = project_store.list_projects(get_current_user_id())
    except project_store.ProjectStoreError:
        st.error("Could not load projects.")
        return

    if not projects:
        st.caption("No projects yet.")
        return

    for project in projects:
        project_label = project["name"]
        if project.get("description"):
            project_label = f'{project_label} - {project["description"]}'
        if st.button(project_label, key=f'project_select_{project["id"]}', use_container_width=True):
            st.session_state.active_project_id = project["id"]
            set_active_section(DEFAULT_SECTION)
            st.rerun()


def render_project_history(project_id: int) -> None:
    st.markdown('<div class="workspace-section-title">History Timeline</div>', unsafe_allow_html=True)
    try:
        history_items = project_store.list_project_history(project_id, user_id=get_current_user_id())
    except project_store.ProjectStoreError:
        st.error("Could not load project history.")
        return

    if not history_items:
        st.caption("No project history yet.")
        return

    for item in history_items:
        st.markdown(
            f'<div class="workspace-activity-item">{escape(item["content"])}</div>',
            unsafe_allow_html=True,
        )


def render_project_view(project: dict) -> None:
    st.markdown(
        f"""
        <div class="workspace-title">{escape(project["name"])}</div>
        <div class="workspace-subtitle">{escape(project.get("description") or "No description")}</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="workspace-section-title">Quick Actions</div>', unsafe_allow_html=True)
    if st.button("Analyze Document", key="project_analyze_document", use_container_width=True):
        set_active_section("Documents")
        st.rerun()
    if st.button("Build Prompt", key="project_build_prompt", use_container_width=True):
        set_active_section("Copilot")
        st.rerun()
    if st.button("Create Automation", key="project_create_automation", use_container_width=True):
        set_active_section("Copilot")
        st.rerun()
    if st.button("Executive Analysis", key="project_executive_analysis", use_container_width=True):
        set_active_section("Copilot")
        st.rerun()

    render_project_history(project["id"])


def render_projects_page() -> None:
    active_project = get_active_project()
    if active_project is not None:
        render_project_view(active_project)
        st.markdown('<div class="workspace-section-title">Projects</div>', unsafe_allow_html=True)

    render_new_project_form()
    render_projects_list("Projects List")


def render_workspace() -> None:
    current_user = st.session_state.current_user or {}
    username = st.session_state.username or current_user.get("username", "User")
    try:
        usage = refresh_subscription_usage()
        documents_processed = str(usage["current_document_count"])
        api_requests = str(usage["current_request_count"])
    except (KeyError, ValueError):
        usage = {
            "events": [],
            "subscription_tier": "Starter",
            "current_request_count": 0,
            "monthly_request_limit": 100,
            "current_document_count": 0,
            "monthly_document_limit": 20,
        }
        documents_processed = "0"
        api_requests = "0"

    render_construction_hero(str(username))
    if is_guest_user():
        st.info("Explore sample documents, free rule-based reviews, or real AI analysis with strict daily request and token budgets. Guest AI uses public synthetic evidence only. Private projects and uploads require sign-in.")

    cta_columns = responsive_columns(2)
    with cta_columns[0]:
        if st.button("Open Copilot", key="hero_open_copilot", type="primary", use_container_width=True):
            set_active_section("Copilot")
            st.rerun()
    with cta_columns[1]:
        if st.button("Explore Workspaces", key="hero_explore_workspaces", use_container_width=True):
            if is_guest_user():
                set_active_section("Copilot")
                st.rerun()
            st.session_state["workspace_catalog_open"] = True
            st.rerun()

    with st.container(key="dashboard_metrics"):
        metric_columns = responsive_columns(4)
        metrics = [
            ("Compliance Workflows", "7", "NCC, codes, contracts, tender risk"),
            ("Documents Indexed", documents_processed, "This billing period"),
            ("AI Requests", api_requests, "This billing period"),
            ("Review mode", "Sample" if is_guest_user() else "Live AI", "Free rules; capped public AI" if is_guest_user() else "Uses project evidence and account quota"),
        ]
        for column, (label, value, note) in zip(metric_columns, metrics):
            with column:
                render_metric_card(label, value, note)
    
    render_new_project_form()
    render_projects_list()
    construction_cards = [
        (
            "NCC Compliance",
            "Map project evidence against code obligations and surface missing clauses.",
            "Compliance intelligence",
        ),
        (
            "Building Codes",
            "Review technical requirements, exceptions, and project-specific interpretations.",
            "Code review",
        ),
        (
            "Contracts",
            "Identify obligations, payment terms, delay risk, and negotiation points.",
            "Contract risk",
        ),
        (
            "Tender Analysis",
            "Compare requirements, scope gaps, pricing exposure, and go/no-go signals.",
            "Tender desk",
        ),
        (
            "Risk Assessment",
            "Turn document context into ranked risk registers and executive actions.",
            "Risk controls",
        ),
        (
            "BIM Model Checks",
            "Inspect IFC identifiers, units, dimensions and model data; export element-linked findings.",
            "IFC data quality",
        ),
        (
            "Procurement",
            "Plan supplier decisions, long-lead items, substitutions, and commercial exposure.",
            "Supply workflow",
        ),
    ]
    with st.expander("Construction workflows", expanded=bool(st.session_state.get("workspace_catalog_open"))):
        render_workspace_cards("Construction Workspace", construction_cards)
    if st.button('Open BIM Model Checks',key='open_bim_checks',use_container_width=True):
        set_active_section('BIM');st.rerun()

    business_cards = [
        (
            "Market Research",
            "Summarize market conditions, project pipeline, and opportunity signals.",
            "Growth intelligence",
        ),
        (
            "Competitor Analysis",
            "Profile competitors, capability gaps, and positioning opportunities.",
            "Competitive strategy",
        ),
        (
            "Strategy",
            "Convert commercial context into priorities, roadmaps, and board-ready narratives.",
            "Executive planning",
        ),
        (
            "Sales Intelligence",
            "Draft account plans, qualification notes, and client-facing briefings.",
            "Revenue workflow",
        ),
        (
            "Financial Analysis",
            "Assess margin, exposure, spend, and operating scenarios with clear assumptions.",
            "Commercial lens",
        ),
        (
            "Business Planning",
            "Create structured business plans, operating cadences, and leadership updates.",
            "Planning system",
        ),
    ]
    with st.expander("Business workflows", expanded=bool(st.session_state.get("workspace_catalog_open"))):
        render_workspace_cards("Business Workspace", business_cards)

    st.markdown('<div class="workspace-section-title">Quick Actions</div>', unsafe_allow_html=True)
    action_columns = responsive_columns(4)
    actions = [
        (
            "Analyze Document",
            "Index project documents into the ingestion pipeline.",
            "quick_analyze_document",
            "Documents",
            None,
        ),
        (
            "Build Prompt",
            "Ask the AI workspace about project documents and strategy.",
            "quick_upload_file",
            "Copilot",
            None,
        ),
        (
            "Review Workflow",
            "Run a review and download its evidence and calculations.",
            "quick_run_agent",
            "Copilot",
            None,
        ),
        (
            "Executive Analysis",
            "Review account, usage, and executive intelligence.",
            "quick_view_logs",
            "Reports",
            None,
        ),
    ]

    for column, (title, description, key, section, documents_view) in zip(action_columns, actions):
        with column:
            st.markdown(
                f"""
                <div class="quick-action-card">
                    <div class="quick-action-title">{escape(title)}</div>
                    <div class="quick-action-description">{escape(description)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(title, key=key, use_container_width=True):
                set_active_section(section, documents_view)
                st.rerun()

    st.markdown('<div class="workspace-section-title">Recent Activity</div>', unsafe_allow_html=True)
    if st.session_state.history:
        activity_items = []
        for entry in st.session_state.history[:3]:
            label = entry.get("query", "").replace("\n", " ").strip()
            if len(label) > 84:
                label = f"{label[:81]}..."
            activity_items.append(
                f'<div class="workspace-activity-item">{escape(str(entry.get("mode", "AI")))}: {escape(label)}</div>'
            )
        activity_markup = "\n".join(activity_items)
    else:
        activity_markup = '<div class="workspace-activity-item">No activity yet.</div>'

    st.markdown(
        f"""
        <div class="workspace-activity-card">
            {activity_markup}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="workspace-section-title">Subscription Overview</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="workspace-overview-card">
            <div class="workspace-overview-line"><strong>Plan:</strong> {escape(str(usage["subscription_tier"]))}</div>
            <div class="workspace-overview-line"><strong>Usage:</strong> {escape(str(usage["current_request_count"]))} / {escape(format_limit(usage["monthly_request_limit"]))}</div>
            <div class="workspace-overview-line"><strong>Documents:</strong> {escape(str(usage["current_document_count"]))} / {escape(format_limit(usage["monthly_document_limit"]))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_prompt_library() -> None:
    categories = prompt_store.list_categories()
    if not categories:
        st.caption("No prompts available.")
        return

    selected_category = st.selectbox("Category", categories, key="prompt_library_category")
    prompts = prompt_store.list_prompts(selected_category)
    prompt_options = {prompt["name"]: prompt["id"] for prompt in prompts}

    selected_prompt_name = st.selectbox(
        "Prompt",
        list(prompt_options.keys()),
        key="prompt_library_prompt",
    )
    selected_prompt_id = prompt_options[selected_prompt_name]

    if st.button("Load Prompt Template", use_container_width=True):
        if not require_active_project():
            return
        selected_prompt = prompt_store.get_prompt(selected_prompt_id)
        if selected_prompt:
            st.session_state.query = selected_prompt["content"]
            add_active_project_history("prompt", f"Prompt generated: {selected_prompt['name']}")


def render_ai_request_panel() -> None:
    st.markdown('<div class="hub-section-title">AI Workspace</div>', unsafe_allow_html=True)
    if is_guest_user():
        show_login_modal("Sign in to run advanced agent routing and save analysis history.")
        st.stop()
    active_project = get_active_project()
    if active_project is None:
        st.warning("Please create or select a project first.")
        return
    st.caption(f'Project: {active_project["name"]}')

    with st.container(border=True):
        mode = st.radio(
            "Routing Mode",
            ["Fast Mode", "Advanced Agent Routing"],
            index=0,
            horizontal=True,
        )
        is_fast_mode = mode == "Fast Mode"
        mode_name = "Fast" if is_fast_mode else "Advanced"
        st.caption(f"Active mode: {mode_name}")

        query = st.text_area(
            "Request",
            height=220,
            placeholder="Enter a request for the gateway...",
            key="query",
        )
        submitted = st.button("Submit", type="primary", use_container_width=True)

    display_entry = st.session_state.selected_history

    if submitted:
        cleaned_query = query.strip()

        if not cleaned_query:
            st.warning("Please enter a request.")
        elif not require_active_project():
            pass
        else:
            status_placeholder = st.empty()
            try:
                with status_placeholder.container():
                    render_typing_indicator()
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
                add_active_project_history("ai", f"Prompt generated: {cleaned_query[:80]}")
            finally:
                status_placeholder.empty()

    if display_entry:
        display_result(display_entry)


def render_documents_page() -> None:
    st.markdown('<div class="workspace-title">Documents</div>', unsafe_allow_html=True)
    if is_guest_user():
        show_login_modal("Sign in to upload documents, run analysis, and save report outputs.")
        st.stop()
    active_project = get_active_project()
    if active_project is None:
        st.warning("Please create or select a project first.")
        return
    st.caption(f'Project: {active_project["name"]}')

    view_options = ["document", "executive"]
    selected_view = st.radio(
        "Documents View",
        view_options,
        index=view_options.index(st.session_state.get("documents_view", "document")),
        format_func=lambda value: "Document Intelligence" if value == "document" else "Executive Analysis",
        horizontal=True,
    )
    st.session_state.documents_view = selected_view

    if selected_view == "executive":
        render_project_intelligence_review()
    else:
        render_document_analysis()


def _library_project_changed(key):
    change_workspace_project(key)


def select_library_project(page):
    owner=get_current_user_id();projects=project_store.list_projects(owner,limit=1000)
    if not projects:
        st.info('Create a project before adding private files or IFC models.')
        if st.button('Create or select a project',key='library_empty_'+page):
            set_active_section(DEFAULT_SECTION);st.rerun()
        return None
    options=[p['id'] for p in projects];names={p['id']:p['name'] for p in projects}
    active=st.session_state.get('active_project_id')
    if active not in options:
        active=options[0];st.session_state.active_project_id=active;sync_project_session()
    key=f'library_project_{owner}_{page}'
    st.session_state[key]=active
    st.selectbox('Project',options,format_func=lambda value:names[value],key=key,on_change=_library_project_changed,args=(key,))
    return get_active_project()


def render_upload_page() -> None:
    render_page_header('Documents','Retain, index and manage project-owned file versions.')
    if is_guest_user():
        render_demo('Documents',render_pdf_download);return
    project=select_library_project('documents')
    if project is None:return
    st.caption('Project: '+project['name'])
    from document_management_ui import render
    render(get_current_user_id(),project['id'])


def render_bim_page() -> None:
    render_page_header('BIM Model Checks','Real IFC data-quality inspection with element-linked findings.')
    if is_guest_user():
        st.info('Sign in and select a project to inspect a private IFC model. Guest reviews use a synthetic issue log; no guest model is parsed.')
        render_demo('Copilot',render_pdf_download);return
    project=select_library_project('bim')
    if project is None:return
    st.caption('Project: '+project['name'])
    from bim_ui import render
    render(get_current_user_id(),project['id'])


def render_automation_page() -> None:
    st.markdown('<div class="workspace-title">Automations</div>', unsafe_allow_html=True)
    active_project = get_active_project()
    if active_project is None:
        st.warning("Please create or select a project first.")
        return
    st.caption(f'Project: {active_project["name"]}')
    render_automation_intelligence()


def render_marketplace() -> None:
    st.markdown('<div class="workspace-title">AI Marketplace</div>', unsafe_allow_html=True)
    st.markdown('<div class="workspace-subtitle">Popular Templates</div>', unsafe_allow_html=True)

    search_query = st.text_input("Search", key="marketplace_search")
    selected_category = st.selectbox(
        "Categories",
        ["All", *template_store.TEMPLATE_CATEGORIES],
        key="marketplace_category",
    )

    try:
        templates = template_store.list_templates(selected_category, search_query)
    except template_store.TemplateStoreError:
        st.error("Could not load templates.")
        return

    if not templates:
        st.caption("No templates found.")
        return

    for template in templates:
        price = float(template["price"] or 0)
        price_label = "Free" if price == 0 else f"${price:g}"
        st.markdown(
            f"""
            <div class="template-card">
                <div class="template-card-title">{escape(template["name"])}</div>
                <div class="template-card-description">{escape(template["description"])}</div>
                <div class="template-card-meta">{escape(template["category"])} · <span class="template-card-price">{escape(price_label)}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Use Template", key=f'use_template_{template["id"]}', use_container_width=True):
            if price > 0:
                st.info("Premium Template (Coming Soon)")
            elif not require_active_project():
                return
            else:
                template_config = template["config_json"]
                st.session_state.query = template_config
                add_active_project_history(
                    "automation",
                    f"Automation created: {template['name']}",
                )
                st.success("Template copied into the current project automation workspace.")


def render_prompt_builder() -> None:
    st.markdown('<div class="workspace-title">AI Center</div>', unsafe_allow_html=True)
    with st.expander("Prompt Library", expanded=True):
        render_prompt_library()
    with st.expander("Form Builder", expanded=False):
        render_form_builder()
    render_ai_request_panel()


def render_settings() -> None:
    render_page_header(
        "Settings",
        "Account, workspace, usage, and security preferences.",
    )
    if is_guest_user():
        st.info("Sign in to manage your account, usage and private NCC library.")
        if st.button("Sign in to manage account"):show_login_modal()
        return
    current_user = st.session_state.current_user or {}
    st.markdown(
        f"""
        <div class="workspace-overview-card">
            <div class="workspace-overview-line"><strong>Account:</strong> {escape(str(st.session_state.username or current_user.get("username", "User")))}</div>
            <div class="workspace-overview-line"><strong>Role:</strong> {escape(str(st.session_state.role or current_user.get("role", "User")))}</div>
            <div class="workspace-overview-line"><strong>Session:</strong> Persistent cookie login enabled</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    from account_ui import render_username_settings
    updated_user = render_username_settings(current_user)
    if updated_user:
        set_authenticated_user(updated_user, reset_navigation=False)
        st.rerun()
    render_subscription_summary()
    render_ncc_reference_settings()


def render_ncc_reference_settings() -> None:
    st.subheader("Server NCC references")
    st.caption("Save a server-side PDF/TXT file or directory. Analysis reads matching passages automatically. Your computer's paths cannot be read by this website.")
    if is_guest_user():
        st.info("Sign in to save NCC reference settings.")
        return
    try:
        ncc_library.library_root()
    except ncc_library.NCCReferenceError as exc:
        st.info(str(exc))
        return
    user_id = get_current_user_id()
    saved = ncc_library.load_reference(user_id) or {}
    with st.form("ncc_reference_settings"):
        path = st.text_input("NCC server path", value=saved.get("path", ""), help="Relative to the approved NCC root, or an absolute path inside it. Directories include PDF/TXT files immediately inside them.")
        edition = st.text_input("NCC edition and volume", value=saved.get("edition", ""), placeholder="For example: NCC 2022 Volume One")
        st.caption("Relevant excerpts are sent to the configured AI service during analysis. Saving a path alone does not send document contents.")
        submitted = st.form_submit_button("Save and validate NCC path")
    if submitted:
        try:
            count = ncc_library.save_reference(user_id, path, edition)
            st.success(f"Saved. {count} reference file(s) available for analysis.")
        except (ncc_library.NCCReferenceError, OSError) as exc:
            st.error(str(exc))
    if saved and st.button("Disable local NCC references", key="clear_ncc_reference"):
        ncc_library.clear_reference(user_id)
        st.rerun()
    st.caption("PDFs must contain selectable text. File changes are detected at the next analysis. No matching passage means this source cannot support the answer.")
    from ncc_library_ui import render_private_library_controls
    render_private_library_controls(user_id, get_active_project())


def render_billing_page() -> None:
    st.markdown('<div class="workspace-title">Billing</div>', unsafe_allow_html=True)
    st.markdown("## Subscription")
    try:
        usage = refresh_subscription_usage()
    except ValueError:
        st.error("Could not load billing details.")
        return

    tier = str(usage["subscription_tier"])
    document_usage = f'{usage["current_document_count"]} / {format_limit(usage["monthly_document_limit"])}'
    request_usage = f'{usage["current_request_count"]} / {format_limit(usage["monthly_request_limit"])}'
    renewal_date = format_renewal_date(usage["subscription_end"])

    plan_column, usage_column = st.columns([1, 1])
    with plan_column:
        st.markdown(
            f"""
            <div class="pricing-card">
                <h3>Pro Plan</h3>
                <h1>$29/month</h1>
                <p>Current account tier: {escape(tier)}</p>
                <p>Renews {escape(renewal_date)}</p>
                <p>Stripe checkout integration ready.</p>
                <div class="gradient-button-note">Manage subscription from your billing portal.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with usage_column:
        st.markdown(
            f"""
            <div class="usage-card">
                <div class="dashboard-chart-title">Usage This Period</div>
                <p><strong>Documents used:</strong> {escape(document_usage)}</p>
                <p><strong>API requests:</strong> {escape(request_usage)}</p>
                <p><strong>Plan limits:</strong> {escape(format_limit(usage["monthly_document_limit"]))} documents, {escape(format_limit(usage["monthly_request_limit"]))} API requests</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="workspace-section-title">Plans</div>', unsafe_allow_html=True)
    plan_columns = responsive_columns(4)
    for column, (plan_name, plan_details) in zip(plan_columns, subscription_store.PLAN_CATALOG.items()):
        with column:
            features = "<br>".join(escape(feature) for feature in plan_details["features"])
            st.markdown(
                f"""
                <div class="pricing-card">
                    <h3>{escape(plan_name)}</h3>
                    <h1>{escape(str(plan_details["price"]))}</h1>
                    <p>{features}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_logs() -> None:
    if is_guest_user():
        show_login_modal("Sign in to export history and manage saved reports.")
        st.stop()
    st.markdown('<div class="workspace-title">Logs</div>', unsafe_allow_html=True)
    st.markdown('<div class="hub-section-title">Intelligence History</div>', unsafe_allow_html=True)
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
                key=f"settings_history_{index}",
                use_container_width=True,
            ):
                st.session_state.selected_history = entry
                set_active_section("Copilot")
                st.rerun()
    else:
        st.caption("No history yet.")


def render_reports_page() -> None:
    render_page_header(
        "Reports",
        "Structured executive intelligence and saved deliverables.",
    )
    if is_guest_user():
        render_demo("Reports", render_pdf_download)
        return

    if select_library_project("reports") is None:return
    if not st.session_state.history:
        st.markdown(
            """
            <div class="workspace-activity-card">
                <div class="workspace-activity-item">No reports yet.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    search=st.text_input('Find a report',placeholder='Search report titles',key='report_search')
    matching=[(index,item) for index,item in enumerate(st.session_state.history) if search.casefold() in str(item.get('query','')).casefold()]
    st.caption(f'{len(matching)} of {len(st.session_state.history)} loaded reports')
    if not matching:
        st.info('No matching reports. Clear the search to see saved reports.');return
    report_options = {}
    for index, entry in matching:
        label = entry.get("query", "").replace("\n", " ").strip() or "Untitled report"
        if len(label) > 72:
            label = f"{label[:69]}..."
        report_options[f"{index + 1}. {entry.get('mode', 'Report')} - {label}"] = index

    selected_label = st.selectbox("Report", list(report_options.keys()), key="reports_selected")
    selected_entry = st.session_state.history[report_options[selected_label]]
    st.session_state.selected_history = selected_entry

    from ui_theme import saved_time
    st.caption(f"Saved: {saved_time(selected_entry.get('created_at', ''))} · Status: {selected_entry.get('status', 'draft')}")
    render_report_section("Full analysis", str(selected_entry.get("result", "")))
    sources = selected_entry.get("sources", [])
    if sources:
        st.markdown("### Source snapshots")
        st.write(format_sources(sources))
        with st.expander("Evidence saved with this report"):
            for source in sources:
                st.write(source.get("metadata", {}))
                st.text(source.get("text", ""))
                st.caption(f"Snapshot SHA-256: {source.get('sha256', '')}")
    render_pdf_download(selected_entry)


def render_ai_copilot_panel() -> None:
    if is_guest_user():
        render_demo("Copilot", render_pdf_download)
        return
    render_page_header(
        "Copilot",
        "AI engineer and business consultant for construction intelligence.",
    )
    active_project = get_active_project()
    if is_guest_user():
        st.markdown(
            """
            <div class="guest-banner">
                Guest mode: try basic Copilot prompts. Sign in to use documents, citations, advanced analysis, and saved reports.
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif active_project is None:
        active_project=select_library_project("copilot")
        if active_project is None:return
    else:
        st.caption(f'Project: {active_project["name"]}')

    chip_columns = responsive_columns(4)
    quick_prompts = [
        ("NCC check", "Review this project for NCC compliance gaps and cite relevant evidence."),
        ("Contract risk", "Summarize the major contract risks, obligations, and negotiation points."),
        ("Tender decision", "Prepare a tender go/no-go analysis with commercial and delivery risks."),
        ("Procurement plan", "Create a procurement risk plan for long-lead items and supplier exposure."),
    ]
    for column, (label, prompt) in zip(chip_columns, quick_prompts):
        with column:
            if st.button(label, key=f"copilot_chip_{label.lower().replace(' ', '_')}", use_container_width=True):
                st.session_state["copilot_draft"] = prompt

    if st.session_state.get('copilot_draft'):
        st.text_area('Review question',key='copilot_draft',height=110)
        st.caption('Edit the question, then run it. Opening a workflow does not consume AI tokens.')
        if st.button('Run selected review',type='primary',disabled=active_project is None):
            st.session_state['copilot_pending_prompt']=st.session_state['copilot_draft']

    chat_markup = []
    if st.session_state.copilot_history:
        for message in st.session_state.copilot_history:
            chat_markup.append(format_chat_bubble("user", str(message.get("prompt", ""))))
            chat_markup.append(format_chat_bubble("assistant", str(message.get("response", ""))))
            chat_markup.append(format_citations(message.get("sources")))
    else:
        chat_markup.append(
            format_chat_bubble(
                "assistant",
                "Ask me to assess compliance, contract exposure, tender risk, procurement constraints, or executive planning. I will keep the answer structured and evidence-aware.",
            )
        )
        chat_markup.append(
            '<div class="quick-chip-row">'
            '<span class="quick-chip">NCC compliance</span>'
            '<span class="quick-chip">Contract risk</span>'
            '<span class="quick-chip">Tender analysis</span>'
            '<span class="quick-chip">Executive brief</span>'
            "</div>"
        )
    st.markdown(
        f'<div class="chat-container">{"".join(chat_markup)}</div>',
        unsafe_allow_html=True,
    )

    user_input = st.chat_input(
        "Ask Gao Intelligence Hub",
        disabled=(active_project is None and not is_guest_user()),
    )
    pending_input = st.session_state.pop("copilot_pending_prompt", "")
    if user_input or pending_input:
        cleaned_input = (user_input or pending_input).strip()
        user_id = str(st.session_state.get("user_id") or "default")

        if not cleaned_input:
            st.warning("Enter a question first.")
        elif active_project is None:
            st.warning("Please create or select a project first.")
            return
        else:
            enforce_copilot_rate_limit()

            typing_placeholder = st.empty()
            with typing_placeholder.container():
                render_typing_indicator()

            started_at = time.perf_counter()
            try:
                analysis_payload = run_advanced_mode(cleaned_input)
                response_text = analysis_payload["result"]
            except Exception as exc:
                response_text = f"Error: {str(exc)}"
            finally:
                st.session_state.copilot_calls += 1
                typing_placeholder.empty()
            elapsed_seconds = time.perf_counter() - started_at

            if response_text.startswith("Error:"):
                st.error(response_text)
            else:
                retrieved_chunks = analysis_payload["sources"]
                source_labels = source_labels_from_retrieval(retrieved_chunks)
                payload = analysis_payload
                display_query = cleaned_input
                try:
                    saved_entry = save_history_entry(display_query, "Copilot", payload, elapsed_seconds)
                except Exception:
                    st.error("Analysis completed, but report storage failed. This draft has not been saved.")
                    st.text(response_text)
                    st.download_button("Download unsaved draft", data=response_text, file_name="unsaved-analysis.txt")
                    return
                st.session_state.copilot_history.append(
                    {
                        "prompt": display_query,
                        "response": response_text,
                        "sources": source_labels,
                    }
                )
                st.session_state.copilot_history = st.session_state.copilot_history[-12:]
                st.session_state.selected_history = saved_entry
                add_active_project_history("copilot", f"Copilot response: {display_query[:80]}")

                if retrieved_chunks:
                    st.markdown("### Sources Used")
                    st.write(format_sources(retrieved_chunks))
                    with st.expander("Extracted context"):
                        st.write(build_context(retrieved_chunks))

                st.rerun()


def display_result(entry: dict) -> None:
    st.markdown('<div class="hub-section-title">Response</div>', unsafe_allow_html=True)
    with st.container(border=True):
        result_metrics = [
            ("Mode", str(entry.get("mode", ""))),
            ("Response Time", f"{entry.get('elapsed_seconds', 0.0):.1f}s"),
            ("Category", str(entry.get("category", ""))),
            ("Confidence", str(entry.get("confidence", ""))),
            ("Version", str(entry.get("version", ""))),
        ]
        if entry.get("agent_mode"):
            result_metrics.append(("Agent Mode", str(entry.get("agent_mode", ""))))

        result_metric_markup = "\n".join(
            f"""
            <div class="subscription-desktop-metric">
                <div class="subscription-desktop-label">{escape(label)}</div>
                <div class="subscription-desktop-value">{escape(value)}</div>
            </div>
            """
            for label, value in result_metrics
        )
        st.markdown(f'<div class="grid">{result_metric_markup}</div>', unsafe_allow_html=True)

        st.markdown("#### Result")
        st.markdown(
            f'<div class="hub-result-body">{escape(str(entry.get("result", ""))).replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )
    render_pdf_download(entry)


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


def build_automation_prompt(automation_definition: dict, values: dict[str, str | list[str]]) -> str:
    formatted_values = {
        key: format_form_value(value)
        for key, value in values.items()
    }
    formatted_values["output_sections"] = "\n".join(
        f"{index}. {section}"
        for index, section in enumerate(automation_definition["output_sections"], start=1)
    )
    return automation_definition["template"].format(**formatted_values)


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


def truncate_document_text(
    document_text: str,
    limit: int = DOCUMENT_TEXT_LIMIT,
) -> tuple[str, bool]:
    if len(document_text) <= limit:
        return document_text, False
    return document_text[:limit], True


def apply_total_document_limit(documents: list[dict]) -> tuple[list[dict], bool]:
    remaining_characters = DOCUMENT_TOTAL_TEXT_LIMIT
    limited_documents = []
    total_truncated = False

    for document in documents:
        document_copy = document.copy()
        text = document_copy["text"]

        if remaining_characters <= 0:
            document_copy["text"] = ""
            document_copy["total_truncated"] = True
            total_truncated = True
        elif len(text) > remaining_characters:
            document_copy["text"] = text[:remaining_characters]
            document_copy["total_truncated"] = True
            total_truncated = True
            remaining_characters = 0
        else:
            document_copy["total_truncated"] = False
            remaining_characters -= len(text)

        limited_documents.append(document_copy)

    return limited_documents, total_truncated


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


def build_project_review_prompt(
    review_type: str,
    documents: list[dict],
    total_truncated: bool,
) -> str:
    documents_text = format_project_documents_for_prompt(documents)
    total_notice = ""
    if total_truncated:
        total_notice = f"\nContent truncated to first {DOCUMENT_TOTAL_TEXT_LIMIT} total characters across uploaded files.\n"

    return f"""Analyze the following project documents as a professional construction and business advisor.

Review Type: {review_type}

Project Documents:
{documents_text}{total_notice}

Provide:
1. Executive Summary
2. Document-by-Document Findings
3. Cross-Document Inconsistencies
4. Commercial Risks
5. Technical Risks
6. Contractual Risks
7. Compliance / NCC Risks
8. Procurement Risks
9. Priority Matrix
10. Recommended Actions"""


def format_project_documents_for_prompt(documents: list[dict]) -> str:
    document_sections = []
    for document in documents:
        notices = []
        if document.get("file_truncated"):
            notices.append(f"File content truncated to first {DOCUMENT_TEXT_LIMIT} characters.")
        if document.get("total_truncated"):
            notices.append(f"Combined document content truncated to first {DOCUMENT_TOTAL_TEXT_LIMIT} characters.")

        notice_text = ""
        if notices:
            notice_text = "\n".join(notices) + "\n"

        document_sections.append(
            f"=== File: {document['file_name']} ===\n{notice_text}{document['text']}"
        )
    return "\n\n".join(document_sections)


def render_document_analysis() -> None:
    if is_guest_user():
        show_login_modal("Sign in to upload documents and generate document intelligence.")
        st.stop()

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
            st.caption(
                f"{uploaded_file.name} · {len(document_text)} characters"
                f" · {'Truncated' if truncated else 'Full text'}"
            )
            if truncated:
                st.warning(f"File content was truncated to first {DOCUMENT_TEXT_LIMIT} characters.")

    if st.button("Generate Document Intelligence Prompt", use_container_width=True):
        if not uploaded_file:
            st.warning("Please upload a document first.")
        elif read_failed:
            st.error("Could not generate a prompt because the uploaded file could not be read.")
        elif not require_active_project():
            return
        elif not consume_document_analysis_or_warn():
            return
        else:
            st.session_state.query = build_document_prompt(
                analysis_type,
                uploaded_file.name,
                truncated_text,
                truncated,
            )
            add_active_project_history("document", f"Document analyzed: {uploaded_file.name}")


def render_project_intelligence_review() -> None:
    if is_guest_user():
        show_upgrade_modal()
        st.stop()

    uploaded_files = st.file_uploader(
        "Upload Project Documents",
        type=["pdf", "txt", "docx", "xlsx"],
        key="project_review_upload",
        accept_multiple_files=True,
    )
    review_type = st.selectbox(
        "Review Type",
        PROJECT_REVIEW_TYPES,
        key="project_review_type",
    )
    agent_mode = st.selectbox(
        "Agent Mode",
        EXECUTIVE_AGENT_MODES,
        key="executive_agent_mode",
    )
    st.caption(EXECUTIVE_AGENT_MODE_DESCRIPTIONS[agent_mode])

    documents = []
    had_file_error = False

    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                document_text = extract_uploaded_document_text(
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                )
                truncated_text, file_truncated = truncate_document_text(document_text)
            except Exception as exc:
                had_file_error = True
                st.error(f"Could not read {uploaded_file.name}: {exc}")
            else:
                st.caption(
                    f"{uploaded_file.name} · {len(document_text)} characters"
                    f" · {'Truncated' if file_truncated else 'Full text'}"
                )
                documents.append(
                    {
                        "file_name": uploaded_file.name,
                        "text": truncated_text,
                        "file_truncated": file_truncated,
                    }
                )

        if any(document["file_truncated"] for document in documents):
            st.warning(f"One or more files were truncated to first {DOCUMENT_TEXT_LIMIT} characters.")

    ready_documents = []
    ready_total_truncated = False
    ready_documents_text = ""
    if documents:
        ready_documents, ready_total_truncated = apply_total_document_limit(documents)
        ready_documents_text = format_project_documents_for_prompt(ready_documents)

    if st.button("Generate Executive Review", use_container_width=True):
        if not uploaded_files:
            st.warning("Please upload at least one project document first.")
        elif not documents:
            st.error("No uploaded project documents could be read.")
        elif not require_active_project():
            return
        elif not consume_document_analysis_or_warn():
            return
        else:
            if ready_total_truncated:
                st.warning(f"Combined document content was truncated to first {DOCUMENT_TOTAL_TEXT_LIMIT} characters.")
            if had_file_error:
                st.warning("Some files could not be read and were excluded from the prompt.")
            st.session_state.query = build_project_review_prompt(
                review_type,
                ready_documents,
                ready_total_truncated,
            )
            add_active_project_history("document", f"Document analyzed: {review_type}")

    if st.button("Run Executive Agent Team", use_container_width=True):
        if not uploaded_files:
            st.warning("Please upload at least one project document first.")
        elif not documents:
            st.error("No uploaded project documents could be read.")
        elif not require_active_project():
            return
        elif not consume_executive_agent_usage_or_warn():
            return
        else:
            if ready_total_truncated:
                st.warning(f"Combined document content was truncated to first {DOCUMENT_TOTAL_TEXT_LIMIT} characters.")
            if had_file_error:
                st.warning("Some files could not be read and were excluded from the agent team input.")
            try:
                from executive_agents import run_executive_agent_team

                status_placeholder = st.empty()
                with status_placeholder.container():
                    render_typing_indicator()
                started_at = time.perf_counter()
                payload = run_executive_agent_team(
                    review_type,
                    ready_documents_text,
                    agent_mode,
                )
                elapsed_seconds = time.perf_counter() - started_at
                status_placeholder.empty()
            except Exception:
                if "status_placeholder" in locals():
                    status_placeholder.empty()
                payload = {
                    "category": "executive",
                    "confidence": 0.0,
                    "result": "Executive agent team failed: unable to reach the LLM provider. Please try again later.",
                    "version": VERSION,
                    "agent_mode": agent_mode,
                }
                elapsed_seconds = 0.0

            st.session_state.query = build_project_review_prompt(
                review_type,
                ready_documents,
                ready_total_truncated,
            )
            save_history_entry(
                st.session_state.query,
                "Executive Agent Team",
                payload,
                elapsed_seconds,
                {"agent_mode": agent_mode},
            )
            add_active_project_history("executive", f"Executive analysis: {review_type}")


def render_form_builder() -> None:
    if is_guest_user():
        show_login_modal("Sign in to build prompts inside a saved project workspace.")
        st.stop()

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
                    placeholder=form_field.get("placeholder", ""),
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
                    placeholder=form_field.get("placeholder", ""),
                )

        if st.form_submit_button("Generate Professional Prompt", use_container_width=True):
            if not require_active_project():
                return
            st.session_state.query = build_prompt_from_form(selected_form, values)
            add_active_project_history("prompt", f"Prompt generated: {selected_form_name}")


def render_automation_intelligence() -> None:
    if is_guest_user():
        show_login_modal("Sign in to create automations and save them to a project.")
        st.stop()

    automation_names = [automation_definition["name"] for automation_definition in AUTOMATION_LIBRARY]
    selected_automation_name = st.selectbox(
        "Automation Type",
        automation_names,
        key="automation_intelligence_type",
    )
    selected_automation = next(
        automation_definition
        for automation_definition in AUTOMATION_LIBRARY
        if automation_definition["name"] == selected_automation_name
    )
    selected_automation_key = "".join(
        character.lower() if character.isalnum() else "_"
        for character in selected_automation_name
    ).strip("_")

    with st.form("automation_intelligence_form"):
        values = {}
        for automation_field in selected_automation["fields"]:
            widget_key = f"automation_{selected_automation_key}_{automation_field['key']}"
            field_type = automation_field["type"]

            if field_type == "text_area":
                values[automation_field["key"]] = st.text_area(
                    automation_field["name"],
                    key=widget_key,
                    height=90,
                    placeholder=automation_field.get("placeholder", ""),
                )
            elif field_type == "selectbox":
                values[automation_field["key"]] = st.selectbox(
                    automation_field["name"],
                    automation_field["options"],
                    key=widget_key,
                )
            elif field_type == "multiselect":
                values[automation_field["key"]] = st.multiselect(
                    automation_field["name"],
                    automation_field["options"],
                    key=widget_key,
                )
            else:
                values[automation_field["key"]] = st.text_input(
                    automation_field["name"],
                    key=widget_key,
                    placeholder=automation_field.get("placeholder", ""),
                )

        if st.form_submit_button("Generate Automation Blueprint", use_container_width=True):
            if not require_active_project():
                return
            st.session_state.query = build_automation_prompt(selected_automation, values)
            add_active_project_history("automation", f"Automation created: {selected_automation_name}")


inject_custom_css()
initialize_auth_state()
try:
    import config

    config.load_environment()
except Exception:
    pass
auth_cookies = initialize_cookie_manager()

# Routing vectors are initialized lazily by authenticated AI requests only.
try:
    user_store.initialize_user_store()
except user_store.UserStoreError:
    st.error("Could not start the user database. Please contact the administrator.")
    st.stop()

restore_authenticated_user_from_cookie(auth_cookies)
ensure_guest_user()

try:
    project_store.initialize_project_store()
except project_store.ProjectStoreError:
    st.error("Could not start the project database. Please contact the administrator.")
    st.stop()

try:
    template_store.initialize_template_store()
except template_store.TemplateStoreError:
    st.error("Could not start the template database. Please contact the administrator.")
    st.stop()

DEFAULTS = {
    "active_section": DEFAULT_SECTION,
    "history": [],
    "selected_history": None,
    "query": "",
    "documents_view": "document",
    "active_project_id": None,
    "copilot_calls": 0,
    "copilot_history": [],
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

prompt_store.initialize_prompt_store()
sync_project_session()

st.session_state["active_section"] = normalize_section(st.session_state.get("active_section"))
if st.session_state.get("nav_selected") != st.session_state["active_section"]:
    st.session_state["nav_selected"] = st.session_state["active_section"]

if is_guest_user() and st.session_state.get("auth_modal_open"):
    render_auth_page(auth_cookies)
    st.stop()

render_auth_header(auth_cookies)

with st.sidebar:
    st.markdown("## Gao Intelligence Hub")

    navigation_options = list(SECTION_TO_NAVIGATION.values())
    st.selectbox(
        "Navigation",
        options=navigation_options,
        key="nav_selected",
        on_change=sync_navigation_selection,
        format_func=lambda option: option,
    )

    if is_guest_user():
        st.caption("Exploring as: Guest")
        st.caption("Role: Isolated sample workspace")
        if st.button("Login / Sign Up", key="sidebar_auth", use_container_width=True):
            show_login_modal("Sign in to unlock projects, uploads, reports, and advanced AI.")
    else:
        current_user = st.session_state.current_user or {}
        st.caption(f"Logged in as: {st.session_state.username or current_user.get('username', 'User')}")
        st.caption(f"Role: {st.session_state.role or current_user.get('role', 'User')}")
        if st.session_state.role == "Admin":render_user_limit_summary()

        projects=project_store.list_projects(get_current_user_id(),limit=1000)
        if projects:
            names={item['id']:item['name'] for item in projects}
            key='workspace_project_'+str(get_current_user_id())
            active=st.session_state.get('active_project_id')
            st.session_state[key]=active if active in names else None
            st.selectbox('Active project',[None]+list(names),format_func=lambda value:names.get(value,'Choose a project'),key=key,on_change=change_workspace_project,args=(key,))
        st.caption('Private workspace · Project-scoped evidence')

active_section = st.session_state["active_section"]
if active_section == DEFAULT_SECTION:
    render_workspace()
elif active_section == "Documents":
    render_upload_page()
elif active_section == "BIM":
    render_bim_page()
elif active_section == "Copilot":
    render_ai_copilot_panel()
elif active_section == "Reports":
    render_reports_page()
elif active_section == "Settings":
    render_settings()
else:
    st.session_state["active_section"] = DEFAULT_SECTION
    render_workspace()

