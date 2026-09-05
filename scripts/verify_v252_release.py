#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BANK_SHA256 = "637e5854ea11ed112cc134308850e184900ff5f771328a02ed1bcfd50a890625"
BANK_PATHS = [
    ROOT / "data/question_bank/master_question_bank.csv",
    ROOT / "data/templates/questions_standard_TLG_audited_v1.csv",
]
EXPECTED_CLASS_NAMES = {"Unity", "Thanksgiving", "Empathy", "Wonder", "Resilience", "Integrity"}


def main() -> None:
    failures = []

    config = json.loads((ROOT / "config/project_config.json").read_text(encoding="utf-8"))
    if config.get("version") != "2.5.2":
        failures.append("config/project_config.json version is not 2.5.2")

    for path in BANK_PATHS:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != EXPECTED_BANK_SHA256:
            failures.append(f"{path.relative_to(ROOT)} does not match the canonical audited bank: {digest}")
        bank = pd.read_csv(path, dtype=str).fillna("")
        if len(bank) != 371 or bank["Question_ID"].nunique() != 371:
            failures.append(f"{path.relative_to(ROOT)} is not the 371-unique-question bank")
        if not bank["Review_Status"].eq("Approved").all():
            failures.append(f"{path.relative_to(ROOT)} has non-Approved Standard Bank rows")

    classes = pd.read_csv(ROOT / "data/reference/classes.csv", dtype=str).fillna("")
    expected_columns = ["Level", "Class_Name", "Active"]
    if list(classes.columns) != expected_columns:
        failures.append(f"class master columns are {list(classes.columns)!r}, expected {expected_columns!r}")
    if len(classes) != 24:
        failures.append(f"class master contains {len(classes)} rows, expected 24")
    for level in ["P3", "P4", "P5", "P6"]:
        names = set(classes.loc[classes["Level"].eq(level), "Class_Name"])
        if names != EXPECTED_CLASS_NAMES:
            failures.append(f"{level} class names do not match the six bundled defaults")

    app = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    initial_teacher_build = app.split("if is_admin:", 1)[0]
    if 'st.Page("pages/Classes.py"' in initial_teacher_build:
        failures.append("Classes is exposed in the Teacher navigation branch")

    create_page = (ROOT / "app/pages/Create_Diagnostic.py").read_text(encoding="utf-8")
    if "Every build method gets the same official Learning Outcome coverage check" not in create_page:
        failures.append("universal LO coverage warning block is missing")

    ai_module = (ROOT / "src/ai_analysis.py").read_text(encoding="utf-8")
    reports_page = (ROOT / "app/pages/Reports_AI.py").read_text(encoding="utf-8")
    if "write them directly to the child" not in ai_module:
        failures.append("child-friendly pupil AI report prompt is missing")
    if "TeacherClassAnalysis" not in ai_module or "analyse_class_with_ai" not in ai_module:
        failures.append("teacher class AI analysis is missing")
    if "Include an AI-assisted teacher report for each selected class" not in reports_page:
        failures.append("teacher report option is missing from Reports")

    assignments_page = (ROOT / "app/pages/Assignments.py").read_text(encoding="utf-8")
    if "Download QR code" not in assignments_page or "Clear assignment links" not in assignments_page:
        failures.append("persistent Assignments page is incomplete")
    persistence_module = (ROOT / "src/persistence.py").read_text(encoding="utf-8")
    if 'PROJECT_ROOT_MARKER_KEY = "scienceDiagnosticProjectRoot"' not in persistence_module or '"App Data"' not in persistence_module or '"Google Forms"' not in persistence_module:
        failures.append("Admin-selectable Google Drive project folder layout is incomplete")
    deployment_page = (ROOT / "app/pages/Deployment.py").read_text(encoding="utf-8")
    if "Select an existing Google Drive folder" not in deployment_page or "Use selected Drive folder" not in deployment_page:
        failures.append("Admin Drive-folder selection UI is incomplete")
    google_module = (ROOT / "src/google_forms_api.py").read_text(encoding="utf-8")
    if 'https://www.googleapis.com/auth/drive.file' in google_module or 'https://www.googleapis.com/auth/drive"' not in google_module:
        failures.append("Google Drive scope does not support selecting an existing folder")

    if (ROOT / ".streamlit/secrets.toml").exists():
        failures.append(".streamlit/secrets.toml is present in the release folder")

    if failures:
        print("V2.5.2 release verification FAILED:")
        for item in failures:
            print(f"- {item}")
        raise SystemExit(1)

    print("V2.5.2 release verification passed.")
    print("- version: 2.5.2")
    print("- Standard Bank: MOE age/scope-audited 371-question CSV, all Approved")
    print("- classes: 24 preloaded timeless P3-P6 classes, no Year/enrolment/Class_Code columns")
    print("- Teacher navigation: Classes hidden")
    print("- LO coverage warning: enabled for all selection methods")
    print("- pupil AI report: child-friendly interpretation / concepts / next steps")
    print("- teacher AI report: class analysis / ranked gaps / recommended actions")
    print("- Google Drive project root: Admin-selectable existing/new folder")
    print("- Drive layout: App Data + Google Forms inside selected root")
    print("- real Streamlit secrets file: absent")


if __name__ == "__main__":
    main()
