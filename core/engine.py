from agents import (
    run_business_agent,
    run_construction_agent,
    run_general_agent,
)
from core.critic import review_output
from core.memory import Memory
from core.planner import plan_skills, plan_tasks
from core.reasoning import build_reasoning_prompt, chunks_to_clauses
from core.report_generator import generate_report
from core.retriever import retrieve_multi
from core.router import route_task
from core.skills import format_skill_context
from core.retriever import is_regulatory_query
from core.vector_store import format_sources
import project_store
from core import ncc_library
from core.ncc_catalog import NCCContextRequired
import hashlib
import json


memory = Memory()


def agent_executor(domain, prompt):
    if domain == "construction":
        return run_construction_agent(prompt)

    if domain == "business":
        return run_business_agent(prompt)

    return run_general_agent(prompt)


def _run_engine(user_id, prompt, document_text=None, *, project_id=None, return_details=False):
    scope = project_store.document_scope(user_id, project_id) if project_id is not None else str(user_id)
    history = memory.get(scope)
    reference_context = ncc_library.load_project_context(user_id, project_id) if project_id is not None else {}
    try:
        retrieved_chunks = (
        retrieve_multi(scope, prompt, reference_user_id=user_id, reference_context=reference_context)
        if project_id is not None else retrieve_multi(scope, prompt)
        )
    except NCCContextRequired as exc:
        result = "NCC project context required: " + str(exc)
        payload = {"result": result, "sources": [], "category": "copilot", "version": "2.0", "status": "context_required"}
        return payload if return_details else result
    coverage_warnings = sorted({warning for chunk in retrieved_chunks for warning in (chunk.get("metadata") or {}).get("coverage_warnings", [])})
    skill_chain = plan_skills(prompt, is_rag_response=bool(retrieved_chunks))
    clauses = chunks_to_clauses(retrieved_chunks)
    reasoning_prompt = build_reasoning_prompt(prompt, clauses)
    reasoning_prompt = f"{reasoning_prompt}{format_skill_context(skill_chain)}"
    reasoning_prompt += "\nProject NCC context: " + json.dumps(reference_context) + "\nKeep NCC editions and volumes distinct. When catalog references are present, use them as code authorities; other project documents describe project facts and must not override code requirements. Cite filename, PDF page and clause. Do not infer state adoption or approval-date applicability from the current year. If evidence or project context is missing, ask for it."

    if coverage_warnings:
        reasoning_prompt += "\nEvidence coverage warnings: " + json.dumps(coverage_warnings) + "\nDo not claim a complete compliance assessment when references or full external standards remain unresolved."

    if document_text:
        reasoning_prompt = f"{reasoning_prompt}\n\nAdditional document text:\n{document_text}"

    if history:
        reasoning_prompt = f"{reasoning_prompt}\n\nConversation history:\n{history}"

    results = []

    has_regulatory_reference = any(
        (chunk.get("metadata") or {}).get("code")
        or (chunk.get("metadata") or {}).get("type") in {"ncc", "housing"}
        for chunk in retrieved_chunks
    )
    insufficient_evidence = is_regulatory_query(prompt) and not has_regulatory_reference
    tasks = [] if insufficient_evidence else plan_tasks(prompt)
    if insufficient_evidence:
        tasks = []
        results.append({"result": "Insufficient NCC reference found. Upload reference documents for this project or configure a readable NCC reference path. No compliance conclusion has been made."})

    for task in tasks:
        domain = route_task(task)
        result = agent_executor(domain, reasoning_prompt)
        result = review_output(result)

        results.append(
            {
                "task": task,
                "domain": domain,
                "skills": skill_chain,
                "result": result,
            }
        )

    final_output = generate_report(
        {
            "summary": "AI system execution report generated from planner, router, RAG, reasoning, agents, and critic.",
            "skills": skill_chain,
            "clauses": [clause["clause"] for clause in clauses],
            "analysis": "\n\n".join([result["result"] for result in results]),
            "risk": "Not independently assessed. Review the assessment and source evidence.",
            "recommendations": "Human review required before any compliance or commercial decision.",
        }
    )

    if coverage_warnings:
        final_output += "\n\nEvidence coverage limitations\n" + "\n".join(coverage_warnings)

    sources = []
    for chunk in retrieved_chunks:
        snapshot = {"text": chunk.get("text", ""), "metadata": dict(chunk.get("metadata") or {})}
        snapshot["sha256"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        sources.append(snapshot)
    if sources:
        final_output += "\n\nSources\n" + format_sources(sources)
    memory.add(scope, "user", prompt)
    memory.add(scope, "assistant", final_output)
    if return_details:
        return {"result": final_output, "sources": sources, "category": "copilot", "version": "2.0", "status": "insufficient_evidence" if insufficient_evidence else "draft"}
    return final_output


def run_engine(user_id, prompt, document_text=None, *, project_id=None, return_details=False):
    if project_id is None:
        return _run_engine(user_id,prompt,document_text,project_id=project_id,return_details=return_details)
    project_store.require_project_access(user_id,project_id)
    from core.private_ai import scope
    with scope(user_id,project_id):
        return _run_engine(user_id,prompt,document_text,project_id=project_id,return_details=return_details)
