---
name: upload-ui
description: Build Streamlit document upload interfaces, file uploader workflows, document intelligence panels, upload validation states, extracted-text summaries, mobile-readable uploader styling, and project-bound document analysis UX.
---

# Upload UI

Use this skill when creating or refining upload flows for documents, spreadsheets, reports, proposals, contracts, tenders, or project files.

## Workflow

1. Make the upload target obvious: supported file types, selected analysis mode, and project context.
2. Validate files before downstream actions.
3. Show file name, extracted character count, and truncation status after parsing.
4. Keep the generate/analyze button disabled by logic rather than hiding errors.
5. If project binding exists, require an active project before consuming usage or calling AI.

## Streamlit Rules

- Use `st.file_uploader(..., type=[...])`.
- Use `accept_multiple_files=True` only for project-level or executive review workflows.
- Keep uploader backgrounds light: `#F8FAFC`, text `#0F172A`, border `#CBD5E1`.
- Catch file parsing exceptions and show a friendly `st.error`.
- Store generated prompts in `st.session_state.query` only after validation succeeds.

## Resources

- Read `components/streamlit_patterns.md` for uploader validation patterns.
- Use `templates/streamlit_upload_panel.py` for a safe upload panel starter.
