# Design System

## Tokens

Use these values as the default dark SaaS theme:

```css
:root {
  --app-bg: #0f1115;
  --sidebar-bg: #11141a;
  --surface: #1a1d23;
  --surface-elevated: #222630;
  --surface-soft: #171a20;
  --border: rgba(255, 255, 255, 0.10);
  --border-strong: rgba(255, 255, 255, 0.18);
  --text-title: #ffffff;
  --text-body: #d1d5db;
  --text-muted: #9ca3af;
  --primary: #60a5fa;
  --primary-strong: #3b82f6;
  --success: #34d399;
  --warning: #fbbf24;
  --danger: #f87171;
  --radius-md: 12px;
  --radius-lg: 16px;
  --shadow-card: 0 18px 50px rgba(0, 0, 0, 0.28);
}
```

## Layout

Use one shell for every authenticated page:

```css
html, body {
  width: 100%;
  overflow-x: hidden !important;
  background: var(--app-bg);
}

.block-container {
  max-width: 100% !important;
  padding: 24px 28px 40px !important;
}

.enterprise-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 1199px) {
  .enterprise-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .block-container {
    padding: 16px !important;
  }

  .enterprise-grid {
    grid-template-columns: 1fr;
  }
}
```

## Typography

Use large, calm typography:

```css
h1, .enterprise-title {
  color: var(--text-title);
  font-size: clamp(32px, 5vw, 56px);
  line-height: 1.02;
  letter-spacing: 0;
}

h2, .enterprise-section-title {
  color: var(--text-title);
  font-size: clamp(22px, 3vw, 32px);
  line-height: 1.15;
}

p, .enterprise-body {
  color: var(--text-body);
  font-size: clamp(14px, 2vw, 16px);
}

.enterprise-muted {
  color: var(--text-muted);
}
```

## Streamlit Overrides

Apply consistent dark controls without default Streamlit seams:

```css
.stButton > button {
  width: 100%;
  min-height: 48px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: var(--surface-elevated);
  color: var(--text-title);
  font-weight: 650;
}

.stButton > button:hover {
  border-color: var(--primary);
  background: #273044;
}

.stTextInput input,
.stTextArea textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
  width: 100%;
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border-strong) !important;
  background: var(--surface) !important;
  color: var(--text-title) !important;
  box-shadow: none !important;
  outline: none !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
[data-baseweb="input"]:focus-within,
[data-baseweb="textarea"]:focus-within {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.16) !important;
}

.stFileUploader {
  border-radius: var(--radius-lg);
}

.stFileUploader section {
  background: var(--surface-soft) !important;
  border: 1px dashed var(--border-strong) !important;
  color: var(--text-body) !important;
}
```

## Do Not

- Do not use default Streamlit pages without CSS.
- Do not use fixed-width shells.
- Do not mix light cards into the dark UI unless the whole page is intentionally light.
- Do not nest cards.
- Do not put instructional paragraphs in the UI to explain obvious controls.
