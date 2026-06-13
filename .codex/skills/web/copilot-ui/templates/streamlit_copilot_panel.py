import time

import streamlit as st


def render_copilot_panel(run_fast_mode, run_advanced_mode, save_history_entry, require_active_project, consume_ai_request):
    mode = st.radio(
        "Routing Mode",
        ["Fast Mode", "Advanced Agent Routing"],
        horizontal=True,
    )
    query = st.text_area("Request", height=220, key="query")
    submitted = st.button("Submit", type="primary", use_container_width=True)

    if not submitted:
        return None

    cleaned_query = query.strip()
    if not cleaned_query:
        st.warning("Please enter a request.")
        return None
    if not require_active_project():
        return None
    if not consume_ai_request():
        return None

    with st.spinner("Analyzing..."):
        started_at = time.perf_counter()
        payload = run_fast_mode(cleaned_query) if mode == "Fast Mode" else run_advanced_mode(cleaned_query)
        elapsed_seconds = time.perf_counter() - started_at

    return save_history_entry(cleaned_query, mode, payload, elapsed_seconds)
