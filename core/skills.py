PRIMARY_SKILL_RULES = [
    (
        "ncc-compliance",
        (
            "ncc",
            "national construction code",
            "building code",
            "compliance",
            "housing provisions",
        ),
    ),
    (
        "contract-review",
        (
            "contract",
            "agreement",
            "clause",
            "variation",
            "eot",
            "extension of time",
        ),
    ),
    (
        "tender-analysis",
        (
            "tender",
            "bid",
            "rfq",
            "rft",
            "request for tender",
            "proposal",
        ),
    ),
    (
        "business-strategy",
        (
            "business",
            "strategy",
            "growth",
            "revenue",
            "market",
            "marketing",
            "sales",
        ),
    ),
]

CRITIC_REVIEW_SKILL = "critic-review"
REPORT_GENERATOR_SKILL = "report-generator"
RAG_QUALITY_SKILL = "rag-quality"


def route_primary_skill(text: str) -> str | None:
    normalized_text = text.lower()
    for skill_name, keywords in PRIMARY_SKILL_RULES:
        if any(keyword in normalized_text for keyword in keywords):
            return skill_name
    return None


def build_skill_chain(
    text: str,
    *,
    is_rag_response: bool = False,
    client_deliverable: bool = True,
) -> list[str]:
    skills = []
    primary_skill = route_primary_skill(text)
    if primary_skill is not None:
        skills.append(primary_skill)

    if is_rag_response:
        skills.append(RAG_QUALITY_SKILL)

    skills.append(CRITIC_REVIEW_SKILL)

    if client_deliverable:
        skills.append(REPORT_GENERATOR_SKILL)

    return _dedupe_skills(skills)


def _dedupe_skills(skills: list[str]) -> list[str]:
    deduped = []
    for skill in skills:
        if skill not in deduped:
            deduped.append(skill)
    return deduped


def format_skill_context(skills: list[str]) -> str:
    if not skills:
        return ""
    skill_lines = "\n".join(f"* {skill}" for skill in skills)
    return f"\n\nEnterprise skill routing:\n{skill_lines}"
