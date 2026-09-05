from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def _rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


def _linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str):
    r, g, b = (_linear(c) for c in _rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str):
    l1, l2 = sorted([_luminance(a), _luminance(b)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def test_streamlit_theme_is_dark_and_high_contrast():
    config = (ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
    assert 'base = "dark"' in config
    assert 'backgroundColor = "#0B0B0D"' in config
    assert 'textColor = "#F5F5F7"' in config
    assert _contrast("#F5F5F7", "#0B0B0D") >= 7.0
    assert _contrast("#B8B8C0", "#0B0B0D") >= 4.5


def test_ui_css_has_safe_spacing_legibility_and_alignment_contract():
    css = (ROOT / "src/ui.py").read_text(encoding="utf-8")
    assert "font-size: 16px" in css
    assert "padding-top: 3.25rem" in css
    assert "max-width: 1440px" in css
    assert "align-items: stretch" in css
    assert "min-height: 46px" in css
    assert "overflow: visible" in css
    assert "font-size: 0.9rem" in css


def test_metric_and_content_cards_share_box_sizing_rules():
    css = (ROOT / "src/ui.py").read_text(encoding="utf-8")
    combined_rule = re.search(r"\.apple-card,\s*\.metric-card\s*\{([^}]+)\}", css, flags=re.S)
    assert combined_rule, "Shared card rule missing"
    block = combined_rule.group(1)
    assert "box-sizing: border-box" in block
    assert "width: 100%" in block
    assert "height: 100%" in block


def test_v241_navigation_and_ui_copy_contracts():
    nav = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    reports = (ROOT / "app/pages/Reports_AI.py").read_text(encoding="utf-8")
    qbank = (ROOT / "app/pages/Question_Bank.py").read_text(encoding="utf-8")
    home = (ROOT / "app/pages/Home.py").read_text(encoding="utf-8")
    css = (ROOT / "src/ui.py").read_text(encoding="utf-8")
    assert 'title="Reports (AI-enabled)"' in nav
    assert "Parent Reports" not in nav
    assert "Gemini Notebook authoring pack" in qbank
    assert "NotebookLM" not in qbank
    assert '["P3", "P4", "P5", "P6", "All"]' in qbank
    assert "Checkpoint example:" in reports
    assert "never saved to disk" in reports
    assert "workflow_grid" in home
    assert ".workflow-grid" in css
    assert "grid-auto-rows: 1fr" in css
    assert "min-height: 198px" in css


def test_ai_api_keys_are_described_and_handled_as_session_only():
    page = (ROOT / "app/pages/Reports_AI.py").read_text(encoding="utf-8")
    ai_ui = (ROOT / "src/ai_ui.py").read_text(encoding="utf-8")
    config = (ROOT / "config/project_config.json").read_text(encoding="utf-8")
    assert "render_ai_provider_controls" in page
    assert "Session-only" in ai_ui
    assert "not written" in ai_ui
    assert "write_text(api_key" not in ai_ui
    assert "open(api_key" not in ai_ui
    assert '"ai_api_key_storage": "session_only_never_saved"' in config


def test_v252_multi_provider_model_selector_and_defaults():
    ai_ui = (ROOT / "src/ai_ui.py").read_text(encoding="utf-8")
    ai = (ROOT / "src/ai_analysis.py").read_text(encoding="utf-8")
    gemini = (ROOT / "src/gemini_analysis.py").read_text(encoding="utf-8")
    assert "st.select_slider(" in ai_ui
    assert '"Gemini", "OpenAI", "Claude"' in ai
    assert '"gemini-3.5-flash-lite"' in ai
    assert '"gpt-5.6-luna"' in ai
    assert '"claude-sonnet-5"' in ai
    assert 'DEFAULT_GEMINI_MODEL = DEFAULT_AI_MODELS["Gemini"]' in gemini


def test_v243_question_moderation_and_custom_diagnostic_contract():
    qbank = (ROOT / "app/pages/Question_Bank.py").read_text(encoding="utf-8")
    create = (ROOT / "app/pages/Create_Diagnostic.py").read_text(encoding="utf-8")
    reporting = (ROOT / "src/reporting.py").read_text(encoding="utf-8")
    reports_page = (ROOT / "app/pages/Reports_AI.py").read_text(encoding="utf-8")

    assert '"Approve"' in qbank
    assert '"Reject"' in qbank
    assert 'st.button("Edit"' in qbank
    assert '"Comprehensive testing"' in create
    assert '"Diagnostic type"' not in create
    assert 'st.data_editor(' in create
    assert '"Include"' in create
    assert 'diagnostic_use=None' in create
    assert 'family = "Arial"' in reporting
    assert 'Calibri was not detected' not in reports_page


def test_v244_auto_build_and_cumulative_topic_selection_contract():
    create = (ROOT / "app/pages/Create_Diagnostic.py").read_text(encoding="utf-8")
    diagnostic = (ROOT / "src/diagnostic.py").read_text(encoding="utf-8")

    assert '"Auto Build"' in create
    assert '"Manual selection"' in create
    assert '"Question levels to include"' in create
    assert '"Assessment level"' in create
    assert 'select_balanced_questions' in create
    assert 'select_comprehensive_questions' in create
    assert 'cumulative_levels(assessment_level)' in create
    assert 'PRIMARY_LEVELS = ["P3", "P4", "P5", "P6"]' in diagnostic
    assert 'metadata["question_levels"]' not in create  # manifests use safe get/update flow
    assert 'manifest["question_levels"] = metadata.get("question_levels", [active_level])' in create


def test_v245_question_bank_batch_workflow_and_management_contract():
    qbank = (ROOT / "app/pages/Question_Bank.py").read_text(encoding="utf-8")
    helpers = (ROOT / "src/question_bank.py").read_text(encoding="utf-8")

    assert 'st.tabs(["Import & Review", "Manage Question Bank"])' in qbank
    assert 'accept_multiple_files=True' in qbank
    assert '"Approve All"' in qbank
    assert '"Save All"' in qbank
    assert '"Question Bank management"' in qbank
    assert '"Search questions"' in qbank
    assert '"Inspect or edit one question"' in qbank
    assert 'prepare_multiple_imports' in qbank
    assert 'set_questions_review_status' in qbank
    assert 'def prepare_multiple_imports' in helpers
    assert 'def set_questions_review_status' in helpers


def test_rc9_global_vertical_rhythm_contract():
    css = (ROOT / "src/ui.py").read_text(encoding="utf-8")
    assert '/* Global vertical rhythm' in css
    assert '[data-testid="stTextInput"]' in css
    assert '[data-testid="stMultiSelect"]' in css
    assert '[data-testid="stFileUploader"]' in css
    assert '[data-testid="stExpander"]' in css
    assert 'div.stDownloadButton' in css
    assert 'margin-bottom: .9rem' in css
    assert '[data-testid="stHorizontalBlock"]' in css
    assert 'margin-bottom: 1rem' in css
    assert '.block-container hr' in css
    assert 'margin-bottom: 1.8rem' in css
