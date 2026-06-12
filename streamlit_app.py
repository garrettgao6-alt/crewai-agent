import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000/analyze"
REQUEST_TIMEOUT_SECONDS = 60
VERSION = "1.0"


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


st.set_page_config(page_title="CrewAI Agent Gateway", page_icon=":material/hub:")

st.title("CrewAI Agent Gateway")

mode = st.radio(
    "Routing",
    ["Fast Mode", "Advanced Agent Routing"],
    index=0,
    horizontal=True,
)
is_fast_mode = mode == "Fast Mode"
st.write(f"Mode: {'Fast' if is_fast_mode else 'Advanced'}")

query = st.text_area("Input", height=160, placeholder="Enter a request for the gateway...")
submitted = st.button("Submit", type="primary")

if submitted:
    cleaned_query = query.strip()

    if not cleaned_query:
        st.warning("Please enter a request.")
    else:
        try:
            with st.spinner("Analyzing..."):
                if is_fast_mode:
                    payload = run_fast_mode(cleaned_query)
                else:
                    payload = run_advanced_mode(cleaned_query)
        except requests.exceptions.RequestException as exc:
            st.error(f"Request failed: {exc}")
        except ValueError:
            st.error("Request failed: FastAPI returned invalid JSON.")
        else:
            st.subheader("Response")
            st.write("category")
            st.code(str(payload.get("category", "")))
            st.write("confidence")
            st.code(str(payload.get("confidence", "")))
            st.write("version")
            st.code(str(payload.get("version", "")))
            st.write("result")
            st.write(payload.get("result", ""))
