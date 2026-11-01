"""Isolated public demo presentation. No access to private application stores."""
import streamlit as st
from core import public_demo as demo


def render_demo(page="Copilot", pdf_renderer=None):
    st.subheader("Interactive sample workspace")
    st.info(demo.NOTICE)
    st.caption("No registration · 0 AI tokens · Sample reports stay in this browser session only. Refreshing or leaving the session may clear them. Download to keep a copy.")
    case = st.selectbox("Sample project", demo.CASE_NAMES, key="public_demo_case")
    if page == "Documents":
        query = st.text_input("Search sample documents", max_chars=200, placeholder="Try: fire, payment, lift")
        matches = demo.search(case, query)
        st.caption(f"{len(matches)} sample documents found. Keyword matching; no embeddings or AI call.")
        for doc in matches:
            with st.expander(doc["id"], expanded=True):
                st.text(doc["text"])
                st.caption(f"SHA-256: {doc['sha256']}")
                st.download_button(f"Download {doc['id']}", doc["text"], f"sample-{doc['id']}.txt", key=f"sample_doc_{doc['id']}")
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
        report = st.session_state.get("public_demo_result")
        if not report or report["case"] != case or report["workflow"] != workflow or report["delay_days"] != days:
            st.info("Choose a workflow and run a review. Change the project or delay scenario to compare results.")
            return
        if st.button("Save sample report to this session"):
            reports = st.session_state.get("public_demo_reports", [])
            st.session_state["public_demo_reports"] = (reports + [report])[-20:]
            st.success("Sample report saved to this browser session. Open Reports or download it below.")
    st.text(report["result"])
    with st.expander("Evidence and reproducible method", expanded=True):
        st.json(report["calculation"])
        for source in report["sources"]:
            st.text(source["text"])
            st.caption(f"{source['id']} · SHA-256: {source['sha256']}")
    st.download_button("Download sample report JSON", demo.export_report(report), "gao-sample-report.json", mime="application/json")
    st.download_button("Download sample report text", report["result"], "gao-sample-report.txt", mime="text/plain")
    if pdf_renderer:
        pdf_renderer({"result": report["result"], "query": "Synthetic sample review", "mode": "Sample report"})
    st.caption("Method: allowlisted facts + transparent arithmetic and review rules. No web research, autonomous external actions, or real BIM parsing. Signed-in live AI is separate and uses account quotas.")
