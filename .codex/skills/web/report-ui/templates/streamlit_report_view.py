from xml.sax.saxutils import escape

import streamlit as st


def render_report_view(entry: dict, render_download=None) -> None:
    st.markdown('<div class="hub-section-title">Response</div>', unsafe_allow_html=True)
    metrics = [
        ("Mode", str(entry.get("mode", ""))),
        ("Response Time", f"{entry.get('elapsed_seconds', 0.0):.1f}s"),
        ("Category", str(entry.get("category", ""))),
        ("Confidence", str(entry.get("confidence", ""))),
    ]
    metric_markup = "\n".join(
        f"""
        <div class="subscription-desktop-metric">
            <div class="subscription-desktop-label">{escape(label)}</div>
            <div class="subscription-desktop-value">{escape(value)}</div>
        </div>
        """
        for label, value in metrics
    )
    st.markdown(f'<div class="grid">{metric_markup}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="hub-result-body">{escape(str(entry.get("result", ""))).replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True,
    )
    if render_download is not None:
        render_download(entry)
