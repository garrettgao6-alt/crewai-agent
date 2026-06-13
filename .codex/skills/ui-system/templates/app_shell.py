"""Streamlit enterprise SaaS shell template.

Copy the relevant pieces into the target app and adapt function names to
existing routing, auth, and business logic.
"""

from __future__ import annotations

import streamlit as st


NAV_ITEMS = {
    "Dashboard": "dashboard",
    "Copilot": "copilot",
    "Documents": "documents",
    "Reports": "reports",
    "Settings": "settings",
}


def inject_enterprise_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --app-bg: #0f1115;
          --sidebar-bg: #11141a;
          --surface: #1a1d23;
          --surface-elevated: #222630;
          --surface-soft: #171a20;
          --border: rgba(255, 255, 255, 0.10);
          --border-strong: rgba(255, 255, 255, 0.18);
          --text-title: #ffffff;
          --text-body: #d1d5db;
          --text-muted: #9ca3af;
          --primary: #60a5fa;
          --primary-strong: #3b82f6;
          --success: #34d399;
          --warning: #fbbf24;
          --danger: #f87171;
          --radius-md: 12px;
          --radius-lg: 16px;
          --shadow-card: 0 18px 50px rgba(0, 0, 0, 0.28);
        }

        html, body, [data-testid="stAppViewContainer"] {
          width: 100%;
          overflow-x: hidden !important;
          background: var(--app-bg);
          color: var(--text-body);
        }

        .block-container {
          max-width: 100% !important;
          padding: 24px 28px 40px !important;
        }

        [data-testid="stSidebar"] {
          background: var(--sidebar-bg);
          border-right: 1px solid var(--border);
        }

        .enterprise-title {
          color: var(--text-title);
          font-size: clamp(32px, 5vw, 56px);
          line-height: 1.02;
          letter-spacing: 0;
          margin: 0 0 12px;
        }

        .enterprise-subtitle {
          color: var(--text-muted);
          font-size: clamp(16px, 2vw, 19px);
          margin: 0 0 28px;
        }

        .enterprise-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 16px;
        }

        .enterprise-card, .metric-card, .report-section {
          width: 100%;
          max-width: 100%;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 20px;
          box-shadow: var(--shadow-card);
        }

        .metric-card span {
          display: block;
          color: var(--text-muted);
          font-size: 13px;
          margin-bottom: 12px;
        }

        .metric-card strong {
          display: block;
          color: var(--text-title);
          font-size: 30px;
          line-height: 1;
        }

        .metric-card small {
          display: block;
          color: var(--success);
          margin-top: 12px;
        }

        .stButton > button {
          width: 100%;
          min-height: 48px;
          border-radius: var(--radius-md);
          border: 1px solid var(--border);
          background: var(--surface-elevated);
          color: var(--text-title);
          font-weight: 650;
        }

        .stTextInput input,
        .stTextArea textarea,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {
          border-radius: var(--radius-md) !important;
          border: 1px solid var(--border-strong) !important;
          background: var(--surface) !important;
          color: var(--text-title) !important;
          box-shadow: none !important;
          outline: none !important;
        }

        @media (max-width: 1199px) {
          .enterprise-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 768px) {
          .block-container {
            padding: 16px !important;
          }

          .enterprise-grid {
            grid-template-columns: 1fr;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    st.sidebar.markdown("### Gao Intelligence Hub")
    labels = list(NAV_ITEMS.keys())
    current = st.session_state.get("active_page", "dashboard")
    current_label = next((label for label, page in NAV_ITEMS.items() if page == current), "Dashboard")
    selected = st.sidebar.radio(
        "Navigation",
        labels,
        index=labels.index(current_label),
        label_visibility="collapsed",
    )
    st.session_state.active_page = NAV_ITEMS[selected]
    return st.session_state.active_page


def render_app() -> None:
    st.set_page_config(page_title="Gao Intelligence Hub", layout="wide")
    inject_enterprise_css()
    active_page = render_sidebar()

    if active_page == "dashboard":
        render_dashboard()
    elif active_page == "copilot":
        render_copilot()
    elif active_page == "documents":
        render_documents()
    elif active_page == "reports":
        render_reports()
    elif active_page == "settings":
        render_settings()
