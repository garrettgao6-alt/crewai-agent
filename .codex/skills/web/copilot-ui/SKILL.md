---
name: copilot-ui
description: Build Streamlit AI copilot interfaces, chat/request panels, prompt builder flows, routing mode controls, RAG upload/query experiences, project-aware AI workspaces, and response/result panels for Gao Intelligence Hub.
---

# Copilot UI

Use this skill when building an AI Center, copilot panel, RAG question box, or prompt execution workspace.

## Workflow

1. Show the active project before accepting AI input.
2. Keep prompt composition separate from execution.
3. Provide a clear routing mode control only when the backend supports multiple modes.
4. Validate non-empty input before usage checks or API calls.
5. Save outputs into existing history stores instead of creating parallel history systems.

## Streamlit Rules

- Use `st.text_area` for long requests and `st.chat_input` only when the app already has chat message history.
- Use `st.spinner` around API calls.
- Keep `st.session_state.query` as the editable prompt handoff when that pattern exists.
- Use project guards before AI actions.
- Show concise errors for failed network/API responses.

## Resources

- Read `components/streamlit_patterns.md` for request-panel patterns.
- Use `templates/streamlit_copilot_panel.py` for an execution panel starter.
