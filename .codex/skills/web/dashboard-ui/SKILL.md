---
name: dashboard-ui
description: Build or refine Streamlit SaaS workspace dashboards, KPI summaries, project overview pages, quick actions, recent activity panels, responsive card grids, and executive dashboard layouts for Gao Intelligence Hub or similar web apps.
---

# Dashboard UI

Use this skill when creating a Streamlit dashboard or replacing a feature-list homepage with a product workspace.

## Workflow

1. Start with the user's primary workflow, not marketing content.
2. Build a clear page hierarchy: title, subtitle, quick actions, status/usage, recent activity, and next-step panels.
3. Use responsive CSS grid for cards: 4 columns on wide screens, 2 on tablets, 1 on mobile.
4. Keep every card actionable or informational; avoid decorative card clutter.
5. Make dashboard actions update `st.session_state` rather than duplicating business logic.

## Streamlit Rules

- Use `st.session_state.active_section` for page navigation.
- Use `st.button(..., use_container_width=True)` for dashboard actions.
- Keep mobile action buttons full width with at least 56px height.
- Store dashboard state in explicit keys such as `active_project_id`, `selected_history`, or `dashboard_filter`.
- Keep data fetching in store/helper modules where the app already uses that pattern.

## Resources

- Read `components/streamlit_patterns.md` for reusable layout patterns.
- Use `templates/streamlit_dashboard.py` as a starting point for new dashboard pages.
