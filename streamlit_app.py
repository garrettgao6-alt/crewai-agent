import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000/analyze"
REQUEST_TIMEOUT_SECONDS = 60


st.set_page_config(page_title="CrewAI Agent Gateway", page_icon=":material/hub:")

st.title("CrewAI Agent Gateway")

query = st.text_area("Input", height=160, placeholder="Enter a request for the gateway...")
submitted = st.button("Submit", type="primary")

if submitted:
    cleaned_query = query.strip()

    if not cleaned_query:
        st.warning("Please enter a request.")
    else:
        try:
            with st.spinner("Analyzing..."):
                response = requests.post(
                    API_URL,
                    json={"query": cleaned_query},
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                payload = response.json()
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
