"""Page templates for the enterprise Streamlit UI system."""

from __future__ import annotations

import streamlit as st


def metric_card(label: str, value: str, delta: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <span>{label}</span>
          <strong>{value}</strong>
          <small>{delta}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    st.markdown('<h1 class="enterprise-title">Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="enterprise-subtitle">Your workspace intelligence at a glance.</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="enterprise-grid">', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        metric_card("Documents", "128", "+12 this week")
    with cols[1]:
        metric_card("Requests", "2.4k", "+18%")
    with cols[2]:
        metric_card("Agents", "8", "4 active")
    with cols[3]:
        metric_card("Reports", "36", "5 new")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## Quick actions")
    action_cols = st.columns(3)
    with action_cols[0]:
        st.button("Open Copilot", use_container_width=True)
    with action_cols[1]:
        st.button("Upload Documents", use_container_width=True)
    with action_cols[2]:
        st.button("View Reports", use_container_width=True)

    st.markdown("## Recent activity")
    st.markdown(
        """
        <div class="enterprise-card">
          <p>Document processed: Construction Proposal</p>
          <p>Copilot answered: Risk summary</p>
          <p>Report generated: Executive Brief</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_copilot(run_engine, user_id: str) -> None:
    st.markdown('<h1 class="enterprise-title">Copilot</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="enterprise-subtitle">Ask questions, draft strategy, and analyze project context.</p>',
        unsafe_allow_html=True,
    )

    messages = st.session_state.setdefault("copilot_messages", [])
    for message in messages:
        role_class = "chat-user" if message["role"] == "user" else "chat-assistant"
        st.markdown(
            f"""
            <div class="chat-row {role_class}">
              <div class="chat-bubble">{message["content"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    prompt = st.chat_input("Ask Gao Intelligence Hub")
    if prompt:
        messages.append({"role": "user", "content": prompt})
        with st.spinner("Thinking..."):
            response = run_engine(user_id, prompt)
        messages.append({"role": "assistant", "content": str(response)})
        st.rerun()


def render_documents(trigger_ingestion) -> None:
    st.markdown('<h1 class="enterprise-title">Documents</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="enterprise-subtitle">Upload, process, and manage workspace knowledge.</p>',
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "txt", "docx", "csv"],
        accept_multiple_files=True,
    )
    if st.button("Start ingestion", use_container_width=True, disabled=not uploaded_files):
        trigger_ingestion(uploaded_files)

    st.markdown("## File list")
    st.dataframe(
        [
            {"Name": "blueprint.pdf", "Status": "processed", "Chunks": 42},
            {"Name": "proposal.docx", "Status": "pending", "Chunks": 0},
        ],
        use_container_width=True,
    )


def render_reports(report: dict | None = None) -> None:
    st.markdown('<h1 class="enterprise-title">Reports</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="enterprise-subtitle">Structured executive intelligence and recommendations.</p>',
        unsafe_allow_html=True,
    )

    report = report or {
        "Executive Summary": "No report selected.",
        "Clauses": [],
        "Risk": "Pending",
        "Recommendations": [],
    }

    for title in ["Executive Summary", "Clauses", "Risk", "Recommendations"]:
        st.markdown(
            f"""
            <section class="report-section">
              <h3>{title}</h3>
              <div>{report.get(title, "")}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    st.button("Download report", use_container_width=True, disabled=True)


def render_settings() -> None:
    st.markdown('<h1 class="enterprise-title">Settings</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="enterprise-subtitle">Workspace, account, model, and security preferences.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="enterprise-card">
          <h3>Workspace</h3>
          <p>Settings controls should map to real backend capabilities.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth() -> None:
    st.markdown(
        """
        <div class="auth-shell">
          <div class="auth-card">
            <h1>Gao Intelligence Hub</h1>
            <p>Business, Construction & Executive AI Intelligence Platform</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    username = st.text_input("Username or Email")
    password = st.text_input("Password", type="password")
    st.button("Sign In", use_container_width=True, disabled=not username or not password)
