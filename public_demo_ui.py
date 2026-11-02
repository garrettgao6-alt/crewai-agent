"""Isolated public demo presentation. No access to private application stores."""
import streamlit as st
from uuid import uuid4
from core import public_demo as demo
from core import guest_ai

SOURCE_LABELS = {"contract": "Sample contract", "programme": "Sample programme",
                 "checklist": "Sample review checklist", "market": "Sample market summary"}


def render_demo(page="Copilot", pdf_renderer=None):
    st.subheader("Interactive sample workspace")
    st.info(demo.NOTICE)
    st.caption("Free sample reviews use no AI. Live AI has strict shared daily budgets. Reports stay in this browser session only; download to keep a copy.")
    case = st.selectbox("Sample project", demo.CASE_NAMES, key="public_demo_case")
    if page == "Documents":
        query = st.text_input("Search sample documents", max_chars=200, placeholder="Try: fire, payment, lift")
        matches = demo.search(case, query)
        st.caption(f"{len(matches)} sample documents found. Keyword matching; no embeddings or AI call.")
        for doc in matches:
            with st.expander(SOURCE_LABELS.get(doc["id"], "Sample document"), expanded=True):
                st.text(doc["text"])
                st.caption("Public synthetic sample document")
                st.download_button(f"Download {SOURCE_LABELS.get(doc['id'], 'sample document').lower()}", doc["text"], f"sample-{doc['id']}.txt", key=f"sample_doc_{doc['id']}")
        st.info("Sign in and select your own project to upload documents or configure official server NCC references.")
        return
    if page == "Reports":
        reports = [item for item in st.session_state.get("public_demo_reports", []) if item["case"] == case]
        if not reports:
            st.info("No sample reports for this project yet. Open Copilot, run a sample review, then save it to this session.")
            return
        index = st.selectbox("Saved sample report", range(len(reports)), format_func=lambda i: f"{i + 1}. {reports[i]['workflow']}")
        report = reports[index]
    else:
        workflow = st.selectbox("Sample workflow", demo.WORKFLOWS, key="public_demo_workflow")
        days = st.slider("Delay scenario (days)", 0, 90, 7, key="public_demo_days")
        if st.button("Run sample review", type="primary"):
            st.session_state["public_demo_result"] = demo.analyze(case, workflow, days)
        st.markdown("#### Real AI analysis")
        st.caption("Only bundled public samples and your question are sent to the AI provider. Do not enter personal, confidential or customer information. No private uploads, projects, NCC paths, tools or conversation history are available to guest AI.")
        if "guest_ai_session" not in st.session_state:
            st.session_state["guest_ai_session"] = uuid4().hex
        session = st.session_state["guest_ai_session"]
        budget_ready = False
        try:
            budget = guest_ai.usage(session)
            caps = budget["limits"]
            st.caption(f"Daily budget ({budget['day']}, Melbourne): shared {budget['global'][0]}/{caps['global_requests']} requests, {budget['global'][1]:,}/{caps['global_tokens']:,} reserved tokens. This session: {budget['session'][0]}/{caps['session_requests']} requests, {budget['session'][1]:,}/{caps['session_tokens']:,} reserved tokens. Output ≤600 tokens. Resets at midnight Melbourne time.")
            st.caption("Reservations include a conservative input allowance and stay spent after failures. A new browser session can reset its session allowance; it cannot bypass the shared server budget.")
            budget_ready = True
        except guest_ai.GuestAIError as exc:
            st.error(str(exc))
        question = st.text_area("Ask AI about this public sample", value="What are the main risks, missing evidence and recommended next actions?", max_chars=800, key="guest_ai_question")
        if st.button("Run real AI analysis", disabled=not budget_ready, type="primary"):
            st.session_state.pop("public_demo_result", None)
            try:
                with st.spinner("Analyzing public sample with AI…"):
                    st.session_state["public_demo_result"] = guest_ai.analyze(session, case, workflow, question, days)
                st.rerun()
            except guest_ai.GuestAIError as exc:
                st.error(str(exc))
        report = st.session_state.get("public_demo_result")
        if not report or report["case"] != case or report["workflow"] != workflow or report["delay_days"] != days:
            st.info("Choose a workflow and run a review. Change the project or delay scenario to compare results.")
            return
        if st.button("Save sample report to this session"):
            reports = st.session_state.get("public_demo_reports", [])
            st.session_state["public_demo_reports"] = (reports + [report])[-20:]
            st.success("Sample report saved to this browser session. Open Reports or download it below.")
    method = "AI-assisted sample review" if report.get("method") == "public-ai-v1" else "Sample review"
    usage = f"{report['ai_tokens']:,} tokens" if report.get("ai_tokens") is not None else "usage unavailable; full reservation charged"
    st.caption(f"{method} · AI usage: {usage}")
    st.text(report["result"])
    with st.expander("Calculations and supporting evidence", expanded=True):
        calculation = report["calculation"]
        st.markdown(
            "| Measure | Estimate |\n|:--|--:|\n"
            f"| Lead-time gap after programme float | {calculation['lead_gap_weeks']:,} weeks |\n"
            f"| Estimated gross margin | AUD {calculation['gross_margin']:,.0f} |\n"
            f"| Delay damages for {report['delay_days']} days | AUD {calculation['delay_exposure']:,.0f} |"
        )
        st.caption("Estimates use the selected synthetic project and delay scenario. They are not forecasts or compliance conclusions.")
        for source in report["sources"]:
            st.markdown(f"**{SOURCE_LABELS.get(source['id'], 'Supporting sample document')}**")
            st.text(source["text"])
    st.download_button("Download sample report text", report["result"], "gao-sample-report.txt", mime="text/plain")
    if pdf_renderer:
        pdf_renderer({"result": report["result"], "query": "Synthetic sample review", "mode": "Sample report"})
    st.caption("Sample mode uses transparent rules; live mode makes one real, bounded AI call. Both use public synthetic evidence only. No web research, external actions or BIM geometry parsing.")
