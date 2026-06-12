import json
import time

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000/analyze"
REQUEST_TIMEOUT_SECONDS = 60
VERSION = "1.0"
HISTORY_LIMIT = 10


def run_fast_mode(query: str) -> dict:
    from crewai import Crew, Task

    import intelligent_gateway

    task = Task(
        description=query,
        expected_output="A professional detailed response.",
        agent=intelligent_gateway.writer_agent,
    )
    crew = Crew(
        agents=[intelligent_gateway.writer_agent],
        tasks=[task],
        verbose=True,
    )

    try:
        result = crew.kickoff()
    except Exception:
        return {
            "category": "writing",
            "confidence": 1.0,
            "result": "Gateway execution failed: unable to reach the LLM provider. Please try again later.",
            "version": VERSION,
        }

    try:
        output = result.raw
    except AttributeError:
        output = str(result)

    return {
        "category": "writing",
        "confidence": 1.0,
        "result": output,
        "version": VERSION,
    }


def run_advanced_mode(query: str) -> dict:
    response = requests.post(
        API_URL,
        json={"query": query},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def save_history_entry(query: str, mode_name: str, payload: dict, elapsed_seconds: float) -> dict:
    entry = {
        "query": query,
        "mode": mode_name,
        "category": payload.get("category", ""),
        "confidence": payload.get("confidence", ""),
        "version": payload.get("version", ""),
        "result": payload.get("result", ""),
        "elapsed_seconds": elapsed_seconds,
    }
    st.session_state.history.insert(0, entry)
    st.session_state.history = st.session_state.history[:HISTORY_LIMIT]
    st.session_state.selected_history = entry
    return entry


def display_result(entry: dict) -> None:
    st.subheader("Response")
    st.write(f"Mode: {entry.get('mode', '')}")
    st.write(f"Response Time: {entry.get('elapsed_seconds', 0.0):.1f}s")
    st.write("category")
    st.code(str(entry.get("category", "")))
    st.write("confidence")
    st.code(str(entry.get("confidence", "")))
    st.write("version")
    st.code(str(entry.get("version", "")))
    st.write("result")
    st.write(entry.get("result", ""))


st.set_page_config(page_title="Garrett Intelligence Hub", page_icon=":material/hub:")

if "history" not in st.session_state:
    st.session_state.history = []

if "selected_history" not in st.session_state:
    st.session_state.selected_history = None

st.title("Garrett Intelligence Hub")

with st.sidebar:
    st.header("History")

    st.download_button(
        "Export History",
        data=json.dumps(st.session_state.history, indent=2),
        file_name="history.json",
        mime="application/json",
        use_container_width=True,
    )

    if st.button("Clear History", use_container_width=True):
        st.session_state.history = []
        st.session_state.selected_history = None

    if st.session_state.history:
        for index, entry in enumerate(st.session_state.history[:HISTORY_LIMIT]):
            label = entry["query"].replace("\n", " ").strip()
            if len(label) > 60:
                label = f"{label[:57]}..."
            if st.button(
                f"{index + 1}. {entry['mode']} - {label}",
                key=f"history_{index}",
                use_container_width=True,
            ):
                st.session_state.selected_history = entry
    else:
        st.caption("No history yet.")

mode = st.radio(
    "Routing",
    ["Fast Mode", "Advanced Agent Routing"],
    index=0,
    horizontal=True,
)
is_fast_mode = mode == "Fast Mode"
mode_name = "Fast" if is_fast_mode else "Advanced"
st.write(f"Mode: {mode_name}")

query = st.text_area("Input", height=160, placeholder="Enter a request for the gateway...")
submitted = st.button("Submit", type="primary")
display_entry = st.session_state.selected_history

if submitted:
    cleaned_query = query.strip()

    if not cleaned_query:
        st.warning("Please enter a request.")
    else:
        try:
            with st.spinner("Analyzing..."):
                started_at = time.perf_counter()
                if is_fast_mode:
                    payload = run_fast_mode(cleaned_query)
                else:
                    payload = run_advanced_mode(cleaned_query)
                elapsed_seconds = time.perf_counter() - started_at
        except requests.exceptions.RequestException as exc:
            st.error(f"Request failed: {exc}")
        except ValueError:
            st.error("Request failed: FastAPI returned invalid JSON.")
        else:
            display_entry = save_history_entry(
                cleaned_query,
                mode_name,
                payload,
                elapsed_seconds,
            )

if display_entry:
    display_result(display_entry)
