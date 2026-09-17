from pathlib import Path
import hashlib
import json

import pandas as pd

from src.ai_analysis import (
    AI_MODEL_OPTIONS,
    AI_PROVIDERS,
    DEFAULT_AI_MODELS,
    DiagnosticReportAnalysis,
    TeacherClassAnalysis,
    analyse_student_with_ai,
    prepare_anonymous_question_evidence,
    prepare_anonymous_class_evidence,
    build_teacher_class_analysis_prompt,
)
from src.auth import (
    accounts_from_auth_config,
    authenticate_account,
    hash_password,
    is_admin_user,
)

ROOT = Path(__file__).resolve().parents[1]
APPROVED_STANDARD_BANK_SHA256 = "637e5854ea11ed112cc134308850e184900ff5f771328a02ed1bcfd50a890625"


def test_v252_standard_bank_is_371_approved_and_bundled_as_default():
    bank_path = ROOT / "data/question_bank/master_question_bank.csv"
    template_path = ROOT / "data/templates/questions_standard_TLG_audited_v1.csv"
    assert hashlib.sha256(bank_path.read_bytes()).hexdigest() == APPROVED_STANDARD_BANK_SHA256
    assert hashlib.sha256(template_path.read_bytes()).hexdigest() == APPROVED_STANDARD_BANK_SHA256
    bank = pd.read_csv(bank_path, dtype=str).fillna("")
    assert len(bank) == 371
    assert bank["Question_ID"].nunique() == 371
    assert set(bank["Review_Status"]) == {"Approved"}
    assert bank["Approved_By"].eq("Sci Diagnostic MOE Scope & Language Audit").all()
    assert bank["Source_Note"].str.contains("Standard Bank v1: audited against", regex=False).all()
    assert bank["Source_Note"].str.contains("Standard Bank v1: MOE age/scope audit 2026-09-05.", regex=False).all()


def test_v252_has_exactly_teacher_and_admin_shared_accounts():
    teacher_hash = hash_password("teacher-password", salt=b"1111111111111111", iterations=10_000)
    admin_hash = hash_password("admin-password", salt=b"2222222222222222", iterations=10_000)
    accounts = accounts_from_auth_config({
        "teacher": {"password_hash": teacher_hash},
        "admin": {"password_hash": admin_hash},
        "alice": {"password_hash": teacher_hash},
    })
    assert set(accounts) == {"teacher", "admin"}
    assert authenticate_account("teacher", "teacher-password", accounts).role == "teacher"
    admin = authenticate_account("admin", "admin-password", accounts)
    assert admin.role == "admin"
    assert is_admin_user({"role": admin.role})


def test_v252_navigation_and_admin_pages_are_role_guarded():
    app = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    classes = (ROOT / "app/pages/Classes.py").read_text(encoding="utf-8")
    question_bank = (ROOT / "app/pages/Question_Bank.py").read_text(encoding="utf-8")
    deployment = (ROOT / "app/pages/Deployment.py").read_text(encoding="utf-8")
    assert "if is_admin:" in app
    assert 'st.Page("pages/Classes.py"' in app
    assert 'st.Page("pages/Question_Bank.py"' in app
    assert 'st.Page("pages/Deployment.py"' in app
    assert 'Admin access is required for this page.' in classes
    assert 'Admin access is required for this page.' in question_bank
    assert 'Admin access is required for this page.' in deployment
    # Classes is appended only inside the Admin branch, not in the initial teacher list.
    initial_build = app.split("if is_admin:", 1)[0]
    assert 'st.Page("pages/Classes.py"' not in initial_build


def test_v252_ai_provider_catalog_is_three_provider_and_session_key_ui_exists():
    assert AI_PROVIDERS == ("Gemini", "OpenAI", "Claude")
    assert set(DEFAULT_AI_MODELS) == set(AI_PROVIDERS)
    assert all(DEFAULT_AI_MODELS[p] in set(AI_MODEL_OPTIONS[p].values()) for p in AI_PROVIDERS)
    ui = (ROOT / "src/ai_ui.py").read_text(encoding="utf-8")
    assert 'type="password"' in ui
    assert 'st.session_state.setdefault(state_key, "")' in ui
    assert "Forget all session API keys" in ui
    assert "Open {provider} key page" in ui


def test_v252_anonymous_ai_evidence_excludes_local_identity():
    rows = pd.DataFrame([{
        "Response_ID": "RID-1",
        "Pupil_Key": "3A-12",
        "Class_Name": "3A",
        "Index_Number": "12",
        "Timestamp": "2026-09-05",
        "Question_ID": "Q1",
        "Topic_Code": "DIV",
        "LO_ID": "P3-DIV-1",
        "Question_Text": "Which animal has a backbone?",
        "Student_Response": "A",
        "Correct_Option": "A",
        "Correct": True,
    }])
    evidence = prepare_anonymous_question_evidence(rows)
    assert len(evidence) == 1
    assert "Response_ID" not in evidence[0]
    assert "Pupil_Key" not in evidence[0]
    assert "Class_Name" not in evidence[0]
    assert "Index_Number" not in evidence[0]
    assert "Timestamp" not in evidence[0]


def test_v252_each_provider_path_validates_same_report_schema(monkeypatch):
    rows = pd.DataFrame([{
        "Question_ID": "Q1",
        "Question_Text": "Test question",
        "Correct": True,
    }])
    payload = json.dumps({
        "response_pattern_summary": "The supplied response was correct.",
        "concepts_to_revisit": [],
        "suggested_next_steps": ["Try a fresh question on the same concept."],
    })

    import src.ai_analysis as module
    monkeypatch.setattr(module, "_call_gemini", lambda *args, **kwargs: payload)
    monkeypatch.setattr(module, "_call_openai", lambda *args, **kwargs: payload)
    monkeypatch.setattr(module, "_call_claude", lambda *args, **kwargs: payload)

    for provider in AI_PROVIDERS:
        result = analyse_student_with_ai(
            rows,
            provider=provider,
            api_key="session-only-test-key",
            model=DEFAULT_AI_MODELS[provider],
        )
        assert isinstance(result, DiagnosticReportAnalysis)
        assert result.concepts_to_revisit == []


def test_v252_preloads_timeless_classes_without_enrolment_counts():
    from src.classes import load_classes
    classes = load_classes(ROOT / "data/reference/classes.csv")
    assert len(classes) == 24
    assert set(classes["Level"]) == {"P3", "P4", "P5", "P6"}
    assert classes.groupby("Level").size().to_dict() == {"P3": 6, "P4": 6, "P5": 6, "P6": 6}
    assert list(classes.columns) == ["Level", "Class_Name", "Active"]
    assert "Year" not in classes.columns
    assert "Index_Min" not in classes.columns
    assert "Index_Max" not in classes.columns
    assert "Class_Code" not in classes.columns
    expected_names = {"Unity", "Thanksgiving", "Empathy", "Wonder", "Resilience", "Integrity"}
    for level in ["P3", "P4", "P5", "P6"]:
        assert set(classes.loc[classes["Level"].eq(level), "Class_Name"]) == expected_names


def test_v252_class_master_has_no_year_or_visible_code_and_csv_replaces_current_list():
    from src.classes import class_key_from_row, normalize_classes, replace_classes_from_upload
    existing = normalize_classes(pd.DataFrame([
        {"Year": 2026, "Level": "P3", "Class_Name": "Unity", "Active": True},
        {"Year": 2025, "Level": "P3", "Class_Name": "Old", "Active": True},
    ]))
    incoming = normalize_classes(pd.DataFrame([
        {"Year": 2026, "Level": "P4", "Class_Name": "Wonder", "Class_Code": "SHOULD_BE_IGNORED", "Active": True},
    ]))
    out = replace_classes_from_upload(existing, incoming)
    assert list(out.columns) == ["Level", "Class_Name", "Active"]
    assert set(out["Class_Name"]) == {"Wonder"}
    assert {class_key_from_row(row) for _, row in out.iterrows()} == {"P4_WONDER"}


def test_v252_create_diagnostic_uses_teacher_entered_student_count_not_class_enrolment():
    page = (ROOT / "app/pages/Create_Diagnostic.py").read_text(encoding="utf-8")
    assert "Number of pupils taking this diagnostic" in page
    assert "student_counts[code]" in page
    assert "index_min=1" in page
    assert "index_max=student_counts[code]" in page
    assert "Index_Min" not in page
    assert "Index_Max" not in page
    assert "class_key_from_row" in page
    assert '"Class_Code": manifest["class_code"]' not in page


def test_v252_legacy_candidate_standard_bank_is_migrated_to_approved(tmp_path):
    from src.question_bank import ensure_standard_bank_v1
    baseline = pd.read_csv(ROOT / "data/templates/questions_standard_TLG_audited_v1.csv", dtype=str).fillna("")
    legacy = baseline.copy()
    legacy["Review_Status"] = "Candidate"
    legacy["Approved_Date"] = ""
    legacy["Approved_By"] = ""
    master = tmp_path / "master.csv"
    template = tmp_path / "template.csv"
    legacy.to_csv(master, index=False, encoding="utf-8-sig")
    baseline.to_csv(template, index=False, encoding="utf-8-sig")
    changed, message = ensure_standard_bank_v1(master, template)
    assert changed
    migrated = pd.read_csv(master, dtype=str).fillna("")
    assert set(migrated["Review_Status"]) == {"Approved"}
    assert "371" in message


def test_v252_all_question_selection_modes_show_lo_coverage_warning():
    page = (ROOT / "app/pages/Create_Diagnostic.py").read_text(encoding="utf-8")
    # The shared coverage block sits after Auto/Manual selection, not inside only
    # the Comprehensive branch.
    assert "Every build method gets the same official Learning Outcome coverage check" in page
    assert "This diagnostic does not cover" in page
    assert "You may continue if this is intentional" in page
    coverage_pos = page.index("Every build method gets the same official Learning Outcome coverage check")
    assert coverage_pos > page.index('if build_method == "Auto Build":')
    assert coverage_pos > page.index("Tick the questions you want")


def test_v252_pre_audit_standard_bank_is_upgraded_to_attached_audited_bank(tmp_path):
    from src.question_bank import ensure_standard_bank_v1
    baseline = pd.read_csv(ROOT / "data/templates/questions_standard_TLG_audited_v1.csv", dtype=str).fillna("")
    legacy = baseline.copy()
    legacy["Source_Note"] = "Assessment-focused rebuild aligned to official LO_ID and scope notes."
    legacy["Approved_By"] = "Standard Bank v1"
    legacy.loc[0, "Question_Text"] = "OLD WORDING THAT MUST BE UPGRADED"
    legacy.loc[0, "Times_Used"] = "7"
    legacy.loc[0, "Teacher_Notes"] = "Keep my local note"
    master = tmp_path / "master.csv"
    template = tmp_path / "template.csv"
    legacy.to_csv(master, index=False, encoding="utf-8-sig")
    baseline.to_csv(template, index=False, encoding="utf-8-sig")
    changed, message = ensure_standard_bank_v1(master, template)
    assert changed
    upgraded = pd.read_csv(master, dtype=str).fillna("")
    assert upgraded.loc[0, "Question_Text"] == baseline.loc[0, "Question_Text"]
    assert upgraded.loc[0, "Times_Used"] == "7"
    assert upgraded.loc[0, "Teacher_Notes"] == "Keep my local note"
    assert upgraded["Source_Note"].str.contains("Standard Bank v1: audited against", regex=False).all()
    assert "audited" in message.lower()



def test_v252_pupil_ai_prompt_is_explicitly_child_friendly():
    from src.ai_analysis import build_report_analysis_prompt
    prompt = build_report_analysis_prompt([{
        "Level": "P3",
        "Question_ID": "Q1",
        "Question_Text": "Which object is magnetic?",
        "Student_Response": "A",
        "Correct_Option": "B",
        "Correct": False,
        "Official Learning Outcome": "Identify magnetic and non-magnetic materials.",
    }])
    assert "write them directly to the child" in prompt.lower()
    assert "primary-school child" in prompt.lower()
    assert "do not use secondary-school terminology" in prompt.lower()


def test_v252_teacher_class_evidence_is_anonymous_and_precalculated():
    frame = pd.DataFrame([
        {
            "Response_ID": "r1", "Pupil_Key": "P3 Unity|01", "Class_Name": "P3 Unity", "Index_Number": "01",
            "Question_ID": "Q1", "Level": "P3", "Topic_Code": "P3-INT-MAG", "LO_ID": "LO1",
            "Question_Text": "Which object is magnetic?", "Correct_Option": "B", "Student_Response": "A",
            "Correct": False, "Misconception_Linked_Error": True,
            "Official Topic": "Interactions - Magnets", "Official Learning Outcome": "Identify magnetic materials.",
            "Alternative_Conception_Ref": "AC1",
        },
        {
            "Response_ID": "r2", "Pupil_Key": "P3 Unity|02", "Class_Name": "P3 Unity", "Index_Number": "02",
            "Question_ID": "Q1", "Level": "P3", "Topic_Code": "P3-INT-MAG", "LO_ID": "LO1",
            "Question_Text": "Which object is magnetic?", "Correct_Option": "B", "Student_Response": "B",
            "Correct": True, "Misconception_Linked_Error": False,
            "Official Topic": "Interactions - Magnets", "Official Learning Outcome": "Identify magnetic materials.",
            "Alternative_Conception_Ref": "AC1",
        },
    ])
    evidence = prepare_anonymous_class_evidence(frame)
    dumped = json.dumps(evidence)
    assert evidence["class_size"] == 2
    assert evidence["learning_outcome_evidence"][0]["percent_correct"] == 50.0
    assert "P3 Unity" not in dumped
    assert "01" not in dumped
    assert "P3 Unity|01" not in dumped
    prompt = build_teacher_class_analysis_prompt(evidence)
    assert "learning_gaps" in prompt
    assert "recommended_actions" in prompt
    assert "do not recalculate marks" in prompt.lower()


def test_combined_pdf_merges_teacher_and_pupil_reports(tmp_path):
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader
    from src.reporting import combine_pdf_files, combined_report_filename

    first = tmp_path / "teacher.pdf"
    second = tmp_path / "pupil.pdf"
    for path, label in [(first, "Teacher report"), (second, "Pupil report")]:
        c = canvas.Canvas(str(path))
        c.drawString(72, 720, label)
        c.save()

    out = tmp_path / combined_report_filename("WA3")
    combine_pdf_files([first, second], out)
    reader = PdfReader(str(out))
    assert len(reader.pages) == 2
    text0 = reader.pages[0].extract_text() or ""
    text1 = reader.pages[1].extract_text() or ""
    assert "Teacher report" in text0
    assert "Pupil report" in text1
    assert out.name == "science_diagnostic_complete_report_WA3.pdf"


def test_v252_assignments_page_is_available_to_teacher_and_admin():
    app = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    assert 'st.Page("pages/Assignments.py", title="Assignments"' in app
    page = (ROOT / "app/pages/Assignments.py").read_text(encoding="utf-8")
    assert "Persistent history of class diagnostics" in page
    assert "Download QR code" in page
    assert "Open pupil Google Form" in page
    assert "Clear assignment links" in page


def test_v252_assignment_link_clear_preserves_manifest_identity(tmp_path):
    from src.assignments import clear_assignment_links, list_assignments
    from src.google_forms_api import save_form_manifest
    manifest = {
        "form_id":"FORM1", "diagnostic_id":"D1", "title":"Life Cycles — P3 Unity",
        "class_name":"P3 Unity", "level":"P3", "responder_uri":"https://example.test/form",
        "edit_uri":"https://example.test/edit", "created_at":"2026-09-06T00:00:00",
    }
    save_form_manifest(manifest, tmp_path)
    clear_assignment_links(manifest, tmp_path)
    items = list_assignments(tmp_path)
    assert len(items) == 1
    assert items[0]["form_id"] == "FORM1"
    assert items[0]["diagnostic_id"] == "D1"
    assert items[0]["responder_uri"] == ""
    assert items[0]["edit_uri"] == ""
    assert items[0]["links_cleared"] is True


def test_v252_dedicated_drive_folder_and_forms_subfolder_are_configured():
    persistence = (ROOT / "src/persistence.py").read_text(encoding="utf-8")
    create_page = (ROOT / "app/pages/Create_Diagnostic.py").read_text(encoding="utf-8")
    secrets = (ROOT / ".streamlit/secrets.example.toml").read_text(encoding="utf-8")
    assert 'PROJECT_ROOT_MARKER_KEY = "scienceDiagnosticProjectRoot"' in persistence
    assert 'def select_project_root_folder' in persistence
    assert 'def list_drive_folders' in persistence
    assert '"App Data"' in persistence
    assert '"Google Forms"' in persistence
    assert 'drive_folder_id=drive_layout["forms_id"]' in create_page
    assert 'folder_name = "SASJ Science Diagnostic"' not in secrets
    assert 'Admin selects the Google Drive project folder' in secrets


def test_v252_google_drive_root_is_admin_selectable():
    deployment = (ROOT / "app/pages/Deployment.py").read_text(encoding="utf-8")
    persistence = (ROOT / "src/persistence.py").read_text(encoding="utf-8")
    forms = (ROOT / "src/google_forms_api.py").read_text(encoding="utf-8")

    assert "Select an existing Google Drive folder" in deployment
    assert "Use selected Drive folder" in deployment
    assert "Create and use this folder" in deployment
    assert "get_selected_project_root" in deployment
    assert "select_project_root_folder" in deployment
    assert "appProperties has" in persistence
    assert "https://www.googleapis.com/auth/drive\"" in forms
    assert "https://www.googleapis.com/auth/drive.file" not in forms
