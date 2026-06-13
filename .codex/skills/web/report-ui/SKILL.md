---
name: report-ui
description: Build Streamlit report and deliverable interfaces, response result cards, PDF download panels, executive report viewers, history timelines, compliance report layouts, and client-facing report presentation UI.
---

# Report UI

Use this skill when rendering AI output as a client deliverable, executive report, compliance assessment, downloadable PDF, or project timeline item.

## Workflow

1. Put report metadata above the report body.
2. Preserve line breaks and escape user/AI content before injecting HTML.
3. Keep report content readable on mobile with full-width cards.
4. Provide download actions close to the report.
5. For project systems, add concise history entries after successful generation.

## Streamlit Rules

- Use `escape()` from `xml.sax.saxutils` before rendering dynamic HTML.
- Use `st.download_button` for generated files.
- Use `st.container(border=True)` for framed report tools only.
- Avoid nested cards.
- Keep metadata cards responsive with CSS grid, not fixed columns.

## Resources

- Read `components/streamlit_patterns.md` for report body and download patterns.
- Use `templates/streamlit_report_view.py` for a report renderer starter.
