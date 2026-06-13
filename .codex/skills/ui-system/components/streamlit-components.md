# Streamlit Components

Use these snippets as patterns, adapting names to the existing codebase.

## CSS Injection

```python
def inject_enterprise_css() -> None:
    st.markdown(
        """
        <style>
        /* Paste or adapt components/design-system.md tokens here. */
        </style>
        """,
        unsafe_allow_html=True,
    )
```

## Card

```python
def ui_card(title: str, body: str = "", meta: str = "") -> None:
    st.markdown(
        f"""
        <div class="enterprise-card">
          <div class="enterprise-card-meta">{meta}</div>
          <h3>{title}</h3>
          <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
```

CSS:

```css
.enterprise-card {
  width: 100%;
  max-width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-card);
}

.enterprise-card h3 {
  margin: 0 0 8px;
  color: var(--text-title);
  font-size: 18px;
}

.enterprise-card p {
  margin: 0;
  color: var(--text-body);
}

.enterprise-card-meta {
  margin-bottom: 10px;
  color: var(--text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
```

## Metric Card

```python
def metric_card(label: str, value: str, delta: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <span>{label}</span>
          <strong>{value}</strong>
          <small>{delta}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )
```

## Sidebar Navigation

Use native `st.sidebar` for reliability unless the app already has a custom sidebar:

```python
NAV_ITEMS = {
    "Dashboard": "dashboard",
    "Copilot": "copilot",
    "Documents": "documents",
    "Reports": "reports",
    "Settings": "settings",
}

def render_sidebar() -> str:
    st.sidebar.markdown("### Gao Intelligence Hub")
    labels = list(NAV_ITEMS.keys())
    current = st.session_state.get("active_page", "dashboard")
    index = labels.index(next(label for label, page in NAV_ITEMS.items() if page == current))
    label = st.sidebar.radio("Navigation", labels, index=index, label_visibility="collapsed")
    st.session_state.active_page = NAV_ITEMS[label]
    return st.session_state.active_page
```

## Chat Bubble

```python
def chat_bubble(role: str, content: str) -> None:
    css_class = "chat-user" if role == "user" else "chat-assistant"
    st.markdown(
        f"""
        <div class="chat-row {css_class}">
          <div class="chat-bubble">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
```

CSS:

```css
.chat-row {
  display: flex;
  margin: 12px 0;
}

.chat-user {
  justify-content: flex-end;
}

.chat-assistant {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: min(760px, 88%);
  padding: 14px 16px;
  border-radius: 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-body);
}

.chat-user .chat-bubble {
  background: var(--primary-strong);
  color: #ffffff;
}
```

## Structured Report Section

```python
def report_section(title: str, content: str, tone: str = "neutral") -> None:
    st.markdown(
        f"""
        <section class="report-section report-{tone}">
          <h3>{title}</h3>
          <div>{content}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
```
