---
name: auth-ui
description: Build Streamlit authentication interfaces, login/register forms, account limit messaging, session-state auth flows, sign-out controls, and mobile-readable auth pages for Gao Intelligence Hub.
---

# Auth UI

Use this skill when creating or refining Streamlit sign-in, account creation, or authenticated shell UI.

## Workflow

1. Keep unauthenticated pages minimal: product name, subtitle, Sign In tab, Create Account tab.
2. Never expose app tools before authentication succeeds.
3. Write auth state to explicit session keys: `authenticated`, `user_id`, `username`, and `role`.
4. Show friendly errors for invalid credentials and database failures.
5. Keep sign-out in the sidebar and clear user/project/session selection state.

## Streamlit Rules

- Use `st.form` for login and registration submissions.
- Use `type="password"` for password fields.
- Use full-width submit buttons.
- Keep input borders consistent: white background, `#0F172A` text, `#CBD5E1` default border, `#2563EB` focus border.
- Do not store plaintext passwords in UI state or logs.

## Resources

- Read `components/streamlit_patterns.md` for session-state and form patterns.
- Use `templates/streamlit_auth_page.py` for a login/register page starter.
