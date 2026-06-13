# Streamlit Dashboard Patterns

## Workspace Header

Use HTML markup inside `st.markdown(..., unsafe_allow_html=True)` for controlled SaaS headings:

```python
st.markdown(
    f"""
    <div class="workspace-title">Welcome back, {username}</div>
    <div class="workspace-subtitle">Gao Intelligence Hub</div>
    """,
    unsafe_allow_html=True,
)
```

## Responsive Card Grid

Use CSS grid instead of `st.columns` for dashboard cards:

```css
.grid {
  display: grid;
  gap: 16px;
  width: 100%;
}
@media (min-width: 1200px) { .grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 1199px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
```

## Quick Actions

Quick actions should set state and rerun:

```python
if st.button("Analyze Document", use_container_width=True):
    st.session_state.active_section = "documents"
    st.rerun()
```
