# Streamlit Copilot Patterns

## Request Execution Panel

```python
query = st.text_area("Request", key="query", height=220)
submitted = st.button("Submit", type="primary", use_container_width=True)
if submitted:
    cleaned_query = query.strip()
    if not cleaned_query:
        st.warning("Please enter a request.")
```

## Usage Guard Order

Use this order:

1. Validate input.
2. Require active project.
3. Check usage limits.
4. Call the AI backend.
5. Save history.
6. Render result.

## Result Panel

Render response metadata in responsive cards and preserve report content line breaks.
