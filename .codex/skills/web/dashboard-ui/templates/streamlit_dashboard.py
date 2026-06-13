import streamlit as st


def render_dashboard(username: str) -> None:
    st.markdown(
        f"""
        <div class="workspace-title">Welcome back, {username}</div>
        <div class="workspace-subtitle">Gao Intelligence Hub</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="workspace-section-title">Quick Actions</div>', unsafe_allow_html=True)
    for label, section in [
        ("Analyze Document", "documents"),
        ("Build Prompt", "ai"),
        ("Create Automation", "automations"),
        ("Executive Analysis", "documents"),
    ]:
        if st.button(label, key=f"quick_{section}_{label}", use_container_width=True):
            st.session_state.active_section = section
            st.rerun()

    st.markdown('<div class="workspace-section-title">Recent Activity</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="workspace-activity-card">
            <div class="workspace-activity-item">Document Analysis: Construction Proposal</div>
            <div class="workspace-activity-item">Prompt Generated: Marketing Strategy</div>
            <div class="workspace-activity-item">Automation Created: Project Workflow</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
