# Streamlit Report Patterns

## Escaped Report Body

```python
from xml.sax.saxutils import escape

st.markdown(
    f'<div class="hub-result-body">{escape(report_text).replace(chr(10), "<br>")}</div>',
    unsafe_allow_html=True,
)
```

## Metadata Grid

Use a responsive `.grid` wrapper and simple metric card markup. Avoid `st.columns` for mobile-critical layouts.

## Download Button

```python
st.download_button(
    "Download Report PDF",
    data=pdf_bytes,
    file_name="report.pdf",
    mime="application/pdf",
    use_container_width=True,
)
```
