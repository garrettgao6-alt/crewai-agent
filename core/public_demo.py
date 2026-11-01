"""Public synthetic fixtures and deterministic review. No stores, files or AI clients.

This module deliberately cannot accept project IDs, paths, uploads or arbitrary
prompts. Public review is an allowlisted computation over public sample facts.
"""
from copy import deepcopy
from hashlib import sha256
import json

NOTICE = (
    "SYNTHETIC DEMO ONLY. "
    "These documents are invented, not NCC text or legal/compliance advice. "
    "No customer data, server references or credentials are accessed."
)
WORKFLOWS = (
    "NCC Compliance", "Building Codes", "Contracts", "Tender Analysis",
    "Risk Assessment", "BIM Review", "Procurement", "Market Research",
    "Competitor Analysis", "Strategy", "Sales Intelligence",
    "Financial Analysis", "Business Planning",
)
_CASES = {
    "Riverside sample": {
        "contract": "SYNTHETIC Contract C-01: Contract price AUD 2,000,000. Estimated delivery cost AUD 1,700,000. Delay damages AUD 4,000 per day. Payment due 45 days after certification. No aggregate delay damages cap is specified.",
        "programme": "SYNTHETIC Programme P-01: Lift package required in 12 weeks. Quoted supplier lead time 18 weeks. Programme float 2 weeks. BIM review records 7 open fire-service clashes. Fire door schedule has not been approved.",
        "checklist": "SYNTHETIC Review Checklist R-01 (NOT NCC): Obtain an approved fire door schedule and close fire-service coordination issues before sign-off. This educational checklist cannot establish regulatory compliance.",
        "market": "SYNTHETIC Market M-01: 8 invited opportunities; 3 qualified; 1 won. Sample competitor Alpha offers a 14-week lift lead time at AUD 210,000; Beta offers 18 weeks at AUD 190,000. No real company or current market data is represented.",
        "facts": {"price": 2000000, "cost": 1700000, "damages": 4000, "payment_days": 45, "required_weeks": 12, "lead_weeks": 18, "float_weeks": 2, "clashes": 7},
    },
    "Hillview sample": {
        "contract": "SYNTHETIC Contract C-01: Contract price AUD 1,200,000. Estimated delivery cost AUD 1,080,000. Delay damages AUD 2,500 per day. Payment due 30 days after certification. No aggregate delay damages cap is specified.",
        "programme": "SYNTHETIC Programme P-01: Lift package required in 16 weeks. Quoted supplier lead time 14 weeks. Programme float 1 week. BIM review records 2 open fire-service clashes. Fire door schedule has not been approved.",
        "checklist": "SYNTHETIC Review Checklist R-01 (NOT NCC): Obtain an approved fire door schedule and close fire-service coordination issues before sign-off. This educational checklist cannot establish regulatory compliance.",
        "market": "SYNTHETIC Market M-01: 5 invited opportunities; 2 qualified; 0 won. Sample competitor Alpha offers a 14-week lift lead time at AUD 210,000; Beta offers 18 weeks at AUD 190,000. No real company or current market data is represented.",
        "facts": {"price": 1200000, "cost": 1080000, "damages": 2500, "payment_days": 30, "required_weeks": 16, "lead_weeks": 14, "float_weeks": 1, "clashes": 2},
    },
}
CASE_NAMES = tuple(_CASES)


def documents(case: str) -> list[dict]:
    data = _CASES[case]  # Exact allowlist: no paths, fallback or private lookup.
    return [{"id": key, "text": data[key], "sha256": sha256(data[key].encode()).hexdigest()}
            for key in ("contract", "programme", "checklist", "market")]


def search(case: str, query: str) -> list[dict]:
    """Literal keyword search over four bundled samples; never an AI prompt."""
    terms = set(query[:200].lower().split())
    if not terms:
        return documents(case)
    return [doc for doc in documents(case) if any(term in doc["text"].lower() for term in terms)]


def analyze(case: str, workflow: str, delay_days: int = 7) -> dict:
    if workflow not in WORKFLOWS:
        raise ValueError("Unknown public workflow")
    if type(delay_days) is not int or not 0 <= delay_days <= 90:
        raise ValueError("Delay scenario must be 0 to 90 whole days")
    f = _CASES[case]["facts"]
    gap = max(0, f["lead_weeks"] - f["required_weeks"] - f["float_weeks"])
    margin = f["price"] - f["cost"]
    exposure = f["damages"] * delay_days
    findings = {
        "compliance": "Compliance status: NOT DETERMINED. Approved fire door schedule missing; obtain designer approval and assess against the applicable official NCC edition. [programme, checklist]",
        "contract": f"Uncapped delay damages: AUD {f['damages']:,}/day. Payment term: {f['payment_days']} days. Negotiate a liability cap and assess cash-flow exposure. [contract]",
        "programme": f"Lead-time gap after float: {gap} weeks = max(0, {f['lead_weeks']} - {f['required_weeks']} - {f['float_weeks']}). " + ("Confirm an alternative supplier or revise the programme." if gap else "No delay predicted by this simple lead-time rule; confirm the supplier commitment.") + " [programme]",
        "bim": f"{f['clashes']} unresolved fire-service coordination issues. Assign a design owner and require closure evidence. This reads a sample issue log; no BIM model has been parsed. [programme]",
        "financial": f"Baseline gross margin AUD {margin:,} ({margin / f['price']:.1%}). {delay_days}-day scenario damages AUD {exposure:,}; remaining margin AUD {margin - exposure:,}. Excludes tax, overhead, variations and financing. [contract]",
        "market": "Use the synthetic opportunity funnel and supplier comparison for a qualification review. Verify all real-world assumptions before making investment or sales decisions. No live market research has been performed. [market]",
    }
    selections = {
        "NCC Compliance": ("compliance", "bim"), "Building Codes": ("compliance",),
        "Contracts": ("contract", "financial"), "Tender Analysis": ("contract", "programme", "financial"),
        "Risk Assessment": ("compliance", "contract", "programme"), "BIM Review": ("bim",),
        "Procurement": ("programme", "contract"), "Market Research": ("market",),
        "Competitor Analysis": ("market", "programme"), "Strategy": ("market", "financial", "programme"),
        "Sales Intelligence": ("market",), "Financial Analysis": ("financial",),
        "Business Planning": ("financial", "programme", "market"),
    }
    result = "\n\n".join([NOTICE, "Rule-based sample analysis; no AI model was called.", f"{case} | {workflow}"] + [findings[key] for key in selections[workflow]])
    return deepcopy({"case": case, "workflow": workflow, "delay_days": delay_days,
                     "result": result, "sources": documents(case), "ai_tokens": 0,
                     "calculation": {"lead_gap_weeks": gap, "gross_margin": margin, "delay_exposure": exposure},
                     "method": "public-rules-v1"})


def export_report(report: dict) -> str:
    """Recompute from allowlisted inputs; ignore injected result/source fields."""
    clean = analyze(report["case"], report["workflow"], report["delay_days"])
    if report.get("method") == "public-ai-v1":
        # Output is the session-held provider response; evidence is always rebuilt.
        clean.update(result=str(report.get("result", ""))[:16500], method="public-ai-v1",
                     model="gpt-4o-mini", ai_tokens=report.get("ai_tokens"),
                     reserved_tokens=report.get("reserved_tokens"), question=str(report.get("question", ""))[:800])
    return json.dumps(clean, indent=2)
