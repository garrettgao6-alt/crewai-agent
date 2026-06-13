import streamlit as st


def render_upload_panel(extract_text, build_prompt, require_active_project) -> None:
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=["pdf", "txt", "docx", "xlsx"],
        key="document_upload",
    )
    analysis_type = st.selectbox(
        "Analysis Type",
        ["Contract Review", "Tender Review", "Risk Assessment", "Business Analysis"],
        key="document_analysis_type",
    )

    extracted_text = ""
    if uploaded_file:
        try:
            extracted_text = extract_text(uploaded_file.name, uploaded_file.getvalue())
        except Exception as exc:
            st.error(f"Could not read uploaded file: {exc}")
        else:
            st.write(f"File name: {uploaded_file.name}")
            st.write(f"Extracted character count: {len(extracted_text)}")

    if st.button("Generate Document Intelligence Prompt", use_container_width=True):
        if not uploaded_file:
            st.warning("Please upload a document first.")
            return
        if not require_active_project():
            return
        st.session_state.query = build_prompt(analysis_type, uploaded_file.name, extracted_text)
