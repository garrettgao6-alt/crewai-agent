# Streamlit Upload Patterns

## Single File Validation

```python
uploaded_file = st.file_uploader("Upload Document", type=["pdf", "txt", "docx", "xlsx"])
if uploaded_file:
    try:
        file_bytes = uploaded_file.getvalue()
        # extract text with the app's existing parser
    except Exception as exc:
        st.error(f"Could not read uploaded file: {exc}")
```

## Project Guard

Use the app's existing project guard before consuming usage:

```python
if not require_active_project():
    return
```

## Uploader CSS

```css
[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"] {
  background: #F8FAFC !important;
  color: #0F172A !important;
  border-color: #CBD5E1 !important;
}
```
