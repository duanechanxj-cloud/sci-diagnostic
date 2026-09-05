from __future__ import annotations

import html
import streamlit as st

# V2.4: high-contrast, Apple-inspired dark UI.
# The rules intentionally favour legibility and resilient layout over decorative effects.
DARK_APP_CSS = r"""
<style>
:root {
  --app-bg: #0b0b0d;
  --sidebar-bg: #111114;
  --card-bg: #17171b;
  --card-bg-soft: #1c1c21;
  --text: #f5f5f7;
  --muted: #b8b8c0;
  --subtle: #92929c;
  --line: #303038;
  --line-strong: #454550;
  --blue: #2997ff;
  --blue-hover: #4aa8ff;
  --good: #5bd27a;
  --warning: #ffd166;
  --danger: #ff6b6b;
}

html, body, [class*="css"] {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
  font-size: 16px;
}

.stApp {
  background: var(--app-bg);
  color: var(--text);
}

/* Wider adaptive content area with safe top spacing so headings never clip. */
.block-container {
  width: min(100%, 1440px);
  max-width: 1440px;
  padding-top: 3.25rem;
  padding-left: clamp(1rem, 3vw, 3rem);
  padding-right: clamp(1rem, 3vw, 3rem);
  padding-bottom: 5rem;
  overflow: visible;
}

[data-testid="stSidebar"] {
  background: var(--sidebar-bg);
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] * { color: var(--text); }

h1, h2, h3, h4, h5, h6 {
  color: var(--text);
  letter-spacing: -0.025em;
  line-height: 1.18;
}

p, li, label, .stMarkdown, .stText, [data-testid="stWidgetLabel"] {
  color: var(--text);
}

.stCaption, [data-testid="stCaptionContainer"], small {
  color: var(--muted) !important;
  font-size: 0.9rem !important;
  line-height: 1.45 !important;
}

.apple-eyebrow {
  color: var(--blue);
  font-size: 0.9rem;
  line-height: 1.35;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: .09em;
  margin: .25rem 0 .65rem 0;
  padding-top: .2rem;
  overflow: visible;
}

.apple-title {
  font-size: clamp(2.35rem, 4.2vw, 3.8rem);
  line-height: 1.04;
  font-weight: 760;
  letter-spacing: -.055em;
  margin: 0 0 .8rem 0;
  color: var(--text);
  overflow-wrap: anywhere;
}

.apple-subtitle {
  max-width: 900px;
  font-size: 1.08rem;
  line-height: 1.58;
  color: var(--muted);
  margin: 0 0 2rem 0;
}

.apple-card,
.metric-card {
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 22px;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.apple-card {
  min-height: 148px;
  padding: 1.4rem 1.45rem;
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}
.apple-card h3 {
  margin: 0 0 .55rem 0;
  font-size: 1.08rem;
  line-height: 1.35;
}
.apple-card p {
  margin: 0;
  color: var(--muted);
  font-size: .98rem;
  line-height: 1.55;
}

.metric-card {
  min-height: 142px;
  padding: 1.2rem 1.25rem;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}
.metric-card .label {
  font-size: .92rem;
  line-height: 1.35;
  color: var(--muted);
  margin-bottom: .5rem;
}
.metric-card .value {
  font-size: clamp(1.6rem, 2.5vw, 2.05rem);
  line-height: 1.12;
  font-weight: 740;
  letter-spacing: -.04em;
  color: var(--text);
  overflow-wrap: anywhere;
}
.metric-card .detail {
  font-size: .9rem;
  line-height: 1.45;
  color: var(--muted);
  margin-top: .55rem;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  border-radius: 999px;
  padding: .34rem .68rem;
  font-size: .86rem;
  font-weight: 680;
  background: rgba(41,151,255,.14);
  border: 1px solid rgba(41,151,255,.34);
  color: #74b9ff;
}

.step-line {
  color: var(--muted);
  font-size: .98rem;
  line-height: 1.55;
  margin: .2rem 0 1.25rem 0;
  overflow-wrap: anywhere;
}
.small-note { font-size: .92rem; line-height: 1.5; color: var(--muted); }

/* Keep Streamlit columns visually aligned. */
[data-testid="stHorizontalBlock"] {
  align-items: stretch;
  gap: 1rem;
}
[data-testid="column"] {
  min-width: 0;
}
[data-testid="column"] > div {
  width: 100%;
}

/* Global vertical rhythm: keep controls and content blocks from visually touching. */
[data-testid="stTextInput"],
[data-testid="stNumberInput"],
[data-testid="stTextArea"],
[data-testid="stSelectbox"],
[data-testid="stMultiSelect"],
[data-testid="stFileUploader"],
[data-testid="stRadio"],
[data-testid="stCheckbox"],
[data-testid="stSlider"],
[data-testid="stSelectSlider"],
[data-testid="stDateInput"],
[data-testid="stTimeInput"] {
  margin-bottom: .9rem;
}

/* Column/card rows, such as the Question set summary, need breathing room below. */
[data-testid="stHorizontalBlock"] {
  margin-bottom: 1rem;
}

/* Standalone blocks should not sit flush against the next control. */
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stDataEditor"],
[data-testid="stAlert"] {
  margin-bottom: 1rem;
}

div.stButton,
div.stDownloadButton {
  margin-bottom: .9rem;
}

/* Section headings get a little room before the first control that follows them. */
.block-container h2,
.block-container h3 {
  margin-top: 1.35rem;
  margin-bottom: .85rem;
}

/* Dividers separate major workflow sections rather than merely drawing a line. */
.block-container hr {
  margin-top: 1.8rem;
  margin-bottom: 1.8rem;
}


.workflow-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: 1fr;
  gap: 1rem;
  width: 100%;
  margin-bottom: 1rem;
}
.workflow-card {
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 22px;
  box-sizing: border-box;
  min-width: 0;
  min-height: 198px;
  height: 100%;
  padding: 1.4rem 1.45rem;
  display: grid;
  grid-template-rows: minmax(2.9rem, auto) 1fr;
  align-content: start;
}
.workflow-card h3 {
  margin: 0;
  font-size: 1.08rem;
  line-height: 1.35;
  align-self: start;
}
.workflow-card p {
  margin: .65rem 0 0 0;
  color: var(--muted);
  font-size: .98rem;
  line-height: 1.55;
  align-self: start;
}

/* Accessible, consistently sized controls. */
div.stButton > button,
div.stDownloadButton > button,
a[data-testid="stLinkButton"] {
  border-radius: 12px !important;
  min-height: 46px !important;
  padding: .65rem 1rem !important;
  font-size: .98rem !important;
  line-height: 1.2 !important;
  font-weight: 680 !important;
  border: 1px solid var(--line-strong) !important;
  background: var(--card-bg-soft);
  color: var(--text) !important;
}
div.stButton > button:hover,
div.stDownloadButton > button:hover,
a[data-testid="stLinkButton"]:hover {
  border-color: #62626e !important;
  background: #24242a !important;
}
div.stButton > button[kind="primary"] {
  background: var(--blue) !important;
  border-color: var(--blue) !important;
  color: #07111b !important;
}
div.stButton > button[kind="primary"]:hover {
  background: var(--blue-hover) !important;
  border-color: var(--blue-hover) !important;
}

[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
  border-radius: 12px !important;
  min-height: 46px;
  background: var(--card-bg-soft) !important;
  color: var(--text) !important;
  border-color: var(--line-strong) !important;
  font-size: 1rem !important;
}

/* Equal-width tabs where tabs are used. */
[data-baseweb="tab-list"] {
  gap: .55rem;
  width: 100%;
}
[data-baseweb="tab"] {
  flex: 1 1 0;
  min-height: 46px;
  justify-content: center;
  border-radius: 10px 10px 0 0;
  color: var(--muted);
}

[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--card-bg);
}

[data-testid="stMetric"] {
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1rem;
  min-height: 120px;
}

[data-testid="stAlert"] {
  border-radius: 14px;
  font-size: .98rem;
  line-height: 1.5;
}

hr { border-color: var(--line); }

/* Tablet-first responsive rules for classroom use. */
.login-shell {
  width: min(100%, 520px);
  margin: 8vh auto 0 auto;
  padding: 1.5rem;
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 22px;
}

@media (max-width: 1024px) {
  .block-container {
    max-width: 100%;
    padding-top: 2.5rem;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
  }
  [data-testid="column"] {
    flex: 1 1 220px !important;
    min-width: 220px !important;
  }
  [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    overflow-x: auto;
  }
  .workflow-grid { grid-template-columns: 1fr; }
  .workflow-card { min-height: auto; }
}

@media (max-width: 760px) {
  .block-container {
    padding-top: 2.2rem;
    padding-left: .85rem;
    padding-right: .85rem;
  }
  [data-testid="column"] {
    flex-basis: 100% !important;
    min-width: 100% !important;
  }
  .apple-title { font-size: 2.25rem; }
  .apple-subtitle { font-size: 1rem; }
  .metric-card, .apple-card { min-height: auto; }
  .login-shell { margin-top: 3vh; padding: 1.1rem; }
}
</style>
"""


def apply_apple_style():
    """Compatibility name retained from V2.3; applies the V2.4.1 dark design system."""
    st.markdown(DARK_APP_CSS, unsafe_allow_html=True)


def apply_app_style():
    apply_apple_style()


def page_header(title: str, subtitle: str = "", eyebrow: str = "Science Diagnostic"):
    st.markdown(
        f'<div class="apple-eyebrow">{html.escape(eyebrow)}</div>'
        f'<div class="apple-title">{html.escape(title)}</div>'
        + (f'<div class="apple-subtitle">{html.escape(subtitle)}</div>' if subtitle else ""),
        unsafe_allow_html=True,
    )


def card(title: str, text: str):
    st.markdown(
        f'<div class="apple-card"><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, detail: str = ""):
    st.markdown(
        '<div class="metric-card">'
        f'<div class="label">{html.escape(str(label))}</div>'
        f'<div class="value">{html.escape(str(value))}</div>'
        + (f'<div class="detail">{html.escape(str(detail))}</div>' if detail else "")
        + '</div>',
        unsafe_allow_html=True,
    )


def workflow_grid(items):
    """Render equal-sized workflow cards in one responsive CSS grid."""
    blocks = []
    for title, text in items:
        blocks.append(
            '<div class="workflow-card">'
            f'<h3>{html.escape(str(title))}</h3>'
            f'<p>{html.escape(str(text))}</p>'
            '</div>'
        )
    st.markdown('<div class="workflow-grid">' + ''.join(blocks) + '</div>', unsafe_allow_html=True)
