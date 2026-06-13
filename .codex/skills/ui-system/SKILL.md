---
name: ui-system
description: Build or refactor Streamlit applications into a premium enterprise SaaS interface system with dark theme, left sidebar navigation, dashboard, copilot, documents, reports, settings, authentication screens, reusable cards, metrics, tables, chat bubbles, upload controls, and structured report views. Use when Codex needs to create a unified UI system inspired by Stripe, Notion, OpenAI, and Apple, or when a Streamlit app must stop looking like default Streamlit and become a modern card-based workspace.
---

# Enterprise UI System

Use this skill to implement a cohesive Streamlit SaaS interface for Gao Intelligence Hub or similar enterprise AI platforms. The target experience is minimal, spacious, high-contrast, dark, and product-grade: a fixed left sidebar, clean workspace pages, strong typography, quiet cards, and consistent controls.

## Workflow

1. Read the existing Streamlit app before editing.
2. Identify current page routing, session state keys, auth flow, ingestion hooks, report data shape, and AI engine call sites.
3. Load only the resources needed:
   - Use `components/design-system.md` for design tokens, layout rules, and CSS standards.
   - Use `components/streamlit-components.md` for reusable component markup and interaction patterns.
   - Use `templates/app_shell.py` when creating or replacing the main layout shell.
   - Use `templates/page_templates.py` when implementing dashboard, copilot, documents, reports, settings, or auth pages.
4. Preserve business logic. Refactor UI wrappers and routing first; keep engine, ingestion, auth, and persistence calls intact.
5. Verify the result at desktop and mobile breakpoints where tooling allows. At minimum, check that no fixed-width layout causes horizontal overflow.

## Required App Structure

Implement the platform as a single cohesive workspace:

- Left sidebar: Dashboard, Copilot, Documents, Reports, Settings.
- Optional top header: page title, active project/user context, primary action.
- Main content area: full-width responsive grid with cards and sections.
- Auth page: centered login card before the workspace renders.

Avoid mixing multiple layout systems. Do not combine a legacy home page, default Streamlit widgets, and a separate SaaS shell on the same screen.

## Page Requirements

Dashboard:
- Large hero title and concise subtitle.
- KPI cards for documents, requests, agents, and activity.
- Recent activity section.
- Quick actions that route into Copilot, Documents, and Reports.

Copilot:
- ChatGPT-style surface with history, message bubbles, and bottom input.
- Calls `run_engine(user_id, prompt)` or the app's equivalent engine function.
- Supports streaming or simulated progressive response when the backend supports it.

Documents:
- Upload area with clear status.
- File list table with processed/pending/error states.
- Button that triggers the ingestion pipeline already present in the app.

Reports:
- Structured sections: Executive Summary, Clauses, Risk, Recommendations.
- Emphasize high-risk and key recommendation blocks.
- Include a future-facing download button only if it does not imply unsupported backend behavior.

Settings:
- Account, workspace, model, usage, and security sections when data exists.
- Use disabled or "coming soon" states for unsupported controls.

Auth:
- Centered card with `Gao Intelligence Hub`, subtitle, inputs, and a primary button.
- Keep auth controls visually aligned with the rest of the dark SaaS system.

## Visual Standards

Use the dark design system unless the user explicitly asks for a light theme:

- App background: `#0f1115`
- Surface/card: `#1a1d23`
- Elevated surface: `#222630`
- Border: `rgba(255,255,255,0.10)`
- Title text: `#ffffff`
- Body text: `#d1d5db`
- Muted text: `#9ca3af`
- Primary accent: `#60a5fa`
- Radius: `12px` minimum, `16px` for major cards
- Typography: titles `32px+`, subtitles `18px`, body `14px+`

Default Streamlit visuals must be overridden with injected CSS. Hide chrome that makes the app look like a developer tool when appropriate, but do not hide warnings or errors that users need to see.

## Implementation Rules

- Prefer `st.container`, `st.columns`, and `st.markdown` with contained HTML for layout blocks.
- Keep inputs and buttons accessible with visible labels or `label_visibility="collapsed"` only when surrounding context is clear.
- Avoid fixed widths. Use responsive grids, percentages, and `clamp()` typography.
- Keep mobile layouts single-column. Sidebar may collapse to native Streamlit sidebar behavior if a fixed custom sidebar is not practical.
- Use cards for repeated items and grouped controls; do not nest cards inside cards.
- Do not overload pages with marketing copy, decorative gradients, or unrelated widgets.

## Validation

Before finishing:

- Search for hard-coded widths such as `width: 1200px`, `width: 900px`, and `min-width: 800px`.
- Run Python compile checks for modified Streamlit files.
- Run tests if the repository has a test suite.
- Confirm the sidebar routes render: Dashboard, Copilot, Documents, Reports, Settings.
