def generate_report(data: dict) -> str:
    clauses = data.get("clauses", [])
    clause_lines = "\n".join(f"* {clause}" for clause in clauses) if clauses else "* None"
    skills = data.get("skills", [])
    skill_section = ""
    if skills:
        skill_lines = "\n".join(f"* {skill}" for skill in skills)
        skill_section = f"\n\nEnterprise Skill Routing\n{skill_lines}"

    return f"""Compliance Summary
{data.get("summary", "")}{skill_section}

Relevant Clauses
{clause_lines}

Assessment
{data.get("analysis", "")}

Risk Level
{data.get("risk", "AUTO")}

Recommendations
{data.get("recommendations", "AUTO")}"""
