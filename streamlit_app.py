import json
from io import BytesIO
import os
from xml.sax.saxutils import escape
import time

import requests
import streamlit as st

import prompt_store


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/analyze")
REQUEST_TIMEOUT_SECONDS = 60
VERSION = "1.0"
HISTORY_LIMIT = 10
DOCUMENT_TEXT_LIMIT = 12000
DOCUMENT_TOTAL_TEXT_LIMIT = 30000
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


def field(name: str, key: str, field_type: str = "text_input", options: list[str] | None = None) -> dict:
    return {"name": name, "key": key, "type": field_type, "options": options or []}


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


def save_history_entry(
    query: str,
    mode_name: str,
    payload: dict,
    elapsed_seconds: float,
    metadata: dict | None = None,
) -> dict:
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
        Paragraph("Garrett Intelligence Hub", title_style),
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
    report_type = analysis_type or review_type
    if not report_type or not report_content:
        return

    pdf_bytes = build_pdf_report(
        report_type,
        report_content,
        entry.get("agent_mode"),
    )
    file_name = DOCUMENT_PDF_FILENAMES.get(
        report_type,
        PROJECT_REVIEW_PDF_FILENAMES.get(report_type, "executive_review.pdf"),
    )
    st.download_button(
        "Download Report PDF",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
        use_container_width=True,
    )


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --hub-bg: #F8FAFC;
            --hub-card: #FFFFFF;
            --hub-border: #E2E8F0;
            --hub-text: #0F172A;
            --hub-muted: #475569;
            --hub-accent: #2563EB;
            --hub-purple: #7C3AED;
            --hub-success: #16A34A;
            --hub-warning: #EA580C;
            --hub-accent-soft: #EFF6FF;
        }

        .stApp {
            background: var(--hub-bg);
            color: var(--hub-text) !important;
        }

        h1, h2, h3 {
            color: var(--hub-text) !important;
            letter-spacing: 0;
        }

        label, p, span, div {
            color: #0F172A;
        }

        [data-testid="stSidebar"] {
            background: #FFFFFF !important;
            color: #0F172A !important;
        }

        [data-testid="stSidebar"] * {
            color: #0F172A !important;
        }

        section[data-testid="stSidebar"] {
            background: #FFFFFF !important;
            border-right: 1px solid var(--hub-border);
        }

        section[data-testid="stSidebar"] [data-testid="stExpander"] {
            border: 1px solid var(--hub-border);
            border-radius: 8px;
            background: #FFFFFF !important;
            margin-bottom: 12px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
        }

        [data-testid="stExpander"] summary {
            color: #0F172A !important;
            font-weight: 700 !important;
        }

        [data-testid="stExpander"] summary * {
            color: #0F172A !important;
        }

        [data-testid="stSelectbox"] *,
        [data-testid="stTextInput"] *,
        [data-testid="stTextArea"] *,
        [data-testid="stFileUploader"] *,
        [data-testid="stMultiSelect"] *,
        [data-testid="stRadio"] * {
            color: #0F172A !important;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 7px;
            border: 1px solid #CBD5E1;
            font-weight: 600;
            width: 100%;
            color: #0F172A !important;
            background: #FFFFFF;
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            background: var(--hub-accent);
            border-color: var(--hub-accent);
            color: #FFFFFF !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.24);
        }

        .hub-hero {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 34%),
                radial-gradient(circle at top right, rgba(124, 58, 237, 0.10), transparent 30%),
                #FFFFFF;
            border: 1px solid var(--hub-border);
            border-radius: 8px;
            padding: 34px 34px;
            margin: 8px 0 18px;
            box-shadow: 0 14px 40px rgba(15, 23, 42, 0.07);
        }

        .hub-hero h1 {
            color: #0F172A !important;
            font-size: 46px;
            line-height: 1.08;
            margin: 0 0 8px;
            font-weight: 800;
        }

        .hub-hero h2 {
            color: #2563EB !important;
            font-size: 1.35rem;
            margin: 0 0 12px;
            font-weight: 700 !important;
        }

        .hero-subtitle {
            color: #2563EB !important;
            font-weight: 700 !important;
            font-size: 1.35rem;
        }

        .hub-hero p {
            color: #475569 !important;
            font-size: 16px;
            line-height: 1.55;
            max-width: 820px;
            margin: 0;
        }

        .hub-status-grid {
            display: grid;
            gap: 16px;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin: 0 0 18px;
        }

        .hub-status-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 18px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
            display: flex;
            flex-direction: column;
            height: 220px;
            justify-content: space-between;
            min-height: 220px;
            padding: 24px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .hub-card-top {
            align-items: center;
            display: flex;
            height: 48px;
            justify-content: space-between;
        }

        .hub-card-icon {
            align-items: center;
            background: linear-gradient(135deg, #EFF6FF, #F5F3FF);
            border: 1px solid #DBEAFE;
            border-radius: 12px;
            display: inline-flex;
            font-size: 22px;
            height: 48px;
            justify-content: center;
            width: 48px;
        }

        .hub-badge {
            align-items: center;
            background: #DCFCE7;
            border: 1px solid #BBF7D0;
            border-radius: 999px;
            color: #15803D !important;
            display: inline-flex;
            font-size: 12px;
            font-weight: 700;
            height: 36px;
            justify-content: center;
            line-height: 1;
            padding: 0 12px;
        }

        .hub-status-card .title {
            color: #0F172A !important;
            font-size: 18px;
            font-weight: 760;
            line-height: 1.25;
            min-height: 72px;
        }

        .hub-status-card .body {
            color: #475569 !important;
            font-size: 14px;
            line-height: 1.5;
            min-height: 80px;
        }

        @media (hover: hover) and (pointer: fine) {
            .hub-status-card:hover {
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
                transform: translateY(-4px);
            }
        }

        @media (max-width: 1024px) {
            .hub-status-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        .hub-section-title {
            color: #0F172A !important;
            font-size: 19px;
            font-weight: 780;
            margin: 20px 0 8px;
        }

        .hub-result-body {
            background: #FFFFFF;
            border: 1px solid var(--hub-border);
            border-radius: 8px;
            padding: 18px;
            line-height: 1.72;
            color: #0F172A !important;
            white-space: pre-wrap;
            font-size: 15px;
            box-shadow: inset 0 1px 0 rgba(15, 23, 42, 0.02);
        }

        [data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid var(--hub-border);
            border-radius: 8px;
            padding: 14px 16px;
        }

        [data-testid="stMetricLabel"] {
            color: #475569 !important;
            font-weight: 650;
        }

        [data-testid="stMetricValue"] {
            color: #0F172A !important;
            font-weight: 780;
        }

        .hub-mobile-tabs {
            display: none;
            margin: 8px 0 14px;
        }

        .hub-mobile-tabs .tab-row {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 4px;
        }

        .hub-mobile-tabs .tab-pill {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 999px;
            color: #0F172A !important;
            flex: 0 0 auto;
            font-size: 13px;
            font-weight: 700;
            padding: 8px 11px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border-color: #E2E8F0 !important;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }

        @media (max-width: 768px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 1rem !important;
                max-width: 100% !important;
            }

            .hub-hero {
                padding: 22px 18px;
                margin-top: 4px;
            }

            .hub-hero h1 {
                font-size: 31px;
            }

            .hub-hero h2 {
                font-size: 1.1rem;
            }

            .hero-subtitle {
                font-size: 1.1rem;
            }

            .hub-hero p {
                font-size: 14px;
            }

            .hub-mobile-tabs {
                display: block;
            }

            .hub-status-card {
                margin-bottom: 10px;
            }

            .hub-status-grid {
                grid-template-columns: 1fr;
            }

            section[data-testid="stSidebar"] {
                width: min(92vw, 24rem) !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.7rem !important;
            }

            div[data-testid="column"] {
                min-width: 100% !important;
                width: 100% !important;
            }

            div[data-testid="stButton"] > button,
            div[data-testid="stDownloadButton"] > button {
                width: 100% !important;
            }

            textarea {
                min-height: 220px !important;
            }

            [data-testid="stExpander"] {
                overflow: hidden;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="hub-hero">
            <h1>Garrett Intelligence Hub</h1>
            <h2 class="hero-subtitle">Business, Construction &amp; Executive AI Intelligence Platform</h2>
            <p>Transform project documents, business data, and executive workflows into decision-ready intelligence.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_cards() -> None:
    cards = [
        ("🔬", "Business Intelligence", "Market, sales, financial, and operating intelligence."),
        ("🏗️", "Construction Intelligence", "Project, contract, compliance, and delivery analysis."),
        ("📄", "Document Intelligence", "Extract and analyze PDF, DOCX, XLSX, and TXT files."),
        ("🧠", "Executive Decision Support", "Board-ready reports powered by executive agent modes."),
    ]
    card_markup = "\n".join(
        f"""
        <div class="hub-status-card">
            <div class="hub-card-top">
                <div class="hub-card-icon">{icon}</div>
                <div class="hub-badge">Active</div>
            </div>
            <div class="title">{title}</div>
            <div class="body">{body}</div>
        </div>
        """
        for icon, title, body in cards
    )
    st.markdown(
        f'<div class="hub-status-grid">{card_markup}</div>',
        unsafe_allow_html=True,
    )


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


def display_result(entry: dict) -> None:
    st.markdown('<div class="hub-section-title">Response</div>', unsafe_allow_html=True)
    with st.container(border=True):
        metric_columns = st.columns(4)
        metric_columns[0].metric("Mode", str(entry.get("mode", "")))
        metric_columns[1].metric("Response Time", f"{entry.get('elapsed_seconds', 0.0):.1f}s")
        metric_columns[2].metric("Category", str(entry.get("category", "")))
        metric_columns[3].metric("Confidence", str(entry.get("confidence", "")))

        detail_columns = st.columns(2)
        detail_columns[0].metric("Version", str(entry.get("version", "")))
        if entry.get("agent_mode"):
            detail_columns[1].metric("Agent Mode", str(entry.get("agent_mode", "")))

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
            if truncated:
                st.warning(f"File content was truncated to first {DOCUMENT_TEXT_LIMIT} characters.")

    if st.button("Generate Document Intelligence Prompt", use_container_width=True):
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


def render_project_intelligence_review() -> None:
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
                st.write(f"File name: {uploaded_file.name}")
                st.write(f"Extracted character count: {len(document_text)}")
                st.write(f"Truncated: {'Yes' if file_truncated else 'No'}")
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

    if st.button("Run Executive Agent Team", use_container_width=True):
        if not uploaded_files:
            st.warning("Please upload at least one project document first.")
        elif not documents:
            st.error("No uploaded project documents could be read.")
        else:
            if ready_total_truncated:
                st.warning(f"Combined document content was truncated to first {DOCUMENT_TOTAL_TEXT_LIMIT} characters.")
            if had_file_error:
                st.warning("Some files could not be read and were excluded from the agent team input.")
            try:
                from executive_agents import run_executive_agent_team

                with st.spinner("Running executive agent team..."):
                    started_at = time.perf_counter()
                    payload = run_executive_agent_team(
                        review_type,
                        ready_documents_text,
                        agent_mode,
                    )
                    elapsed_seconds = time.perf_counter() - started_at
            except Exception:
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

        if st.form_submit_button("Generate Professional Prompt", use_container_width=True):
            st.session_state.query = build_prompt_from_form(selected_form, values)


def render_automation_intelligence() -> None:
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

    with st.form("automation_intelligence_form"):
        values = {}
        for automation_field in selected_automation["fields"]:
            widget_key = f"automation_{selected_automation_name}_{automation_field['key']}"
            field_type = automation_field["type"]

            if field_type == "text_area":
                values[automation_field["key"]] = st.text_area(
                    automation_field["name"],
                    key=widget_key,
                    height=80,
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
                )

        if st.form_submit_button("Generate Automation Blueprint", use_container_width=True):
            st.session_state.query = build_automation_prompt(selected_automation, values)


st.set_page_config(page_title="Garrett Intelligence Hub", page_icon=":material/hub:")
inject_custom_css()

if "history" not in st.session_state:
    st.session_state.history = []

if "selected_history" not in st.session_state:
    st.session_state.selected_history = None

if "query" not in st.session_state:
    st.session_state.query = ""

prompt_store.initialize_prompt_store()

render_hero()
render_mobile_navigation_tabs()
render_status_cards()

with st.sidebar:
    with st.expander("📚 Prompt Library", expanded=True):
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

            if st.button("Load Prompt Template", use_container_width=True):
                selected_prompt = prompt_store.get_prompt(selected_prompt_id)
                if selected_prompt:
                    st.session_state.query = selected_prompt["content"]
        else:
            st.caption("No prompts available.")

    with st.expander("🧩 Form Builder", expanded=False):
        render_form_builder()

    with st.expander("📄 Document Intelligence", expanded=False):
        render_document_analysis()

    with st.expander("🧠 Executive Intelligence Center", expanded=False):
        render_project_intelligence_review()

    with st.expander("⚙️ Automation Intelligence", expanded=False):
        render_automation_intelligence()

    with st.expander("🕘 Intelligence History", expanded=False):
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

st.markdown('<div class="hub-section-title">Workspace</div>', unsafe_allow_html=True)
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
