def generate_report(data: dict) -> str:
    clauses = data.get("clauses", [])
    clause_lines = "\n".join(f"* {clause}" for clause in clauses) if clauses else "* None"

    return f"""Compliance Summary
{data.get("summary", "")}

Relevant Clauses
{clause_lines}

Assessment
{data.get("analysis", "")}

Risk Level
{data.get("risk", "AUTO")}

Recommendations
{data.get("recommendations", "AUTO")}"""
