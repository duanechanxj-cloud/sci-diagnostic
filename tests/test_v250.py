from pathlib import Path
import zipfile
from io import BytesIO

import pandas as pd

from src.auth import accounts_from_auth_config, authenticate_account, hash_password, verify_password
from src.config import QUESTION_BANK_COLUMNS
from src.curriculum import load_concept_master
from src.persistence import build_state_snapshot, restore_state_snapshot
from src.question_bank import (
    delete_all_questions,
    delete_questions,
    load_question_bank,
    normalize_question_bank,
    validate_question_bank,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v250_assessment_focused_master_and_bundled_bank_are_valid():
    learning_outcomes, _, topics = load_concept_master()
    assert len(learning_outcomes) == 82
    assert learning_outcomes["Official Domain"].value_counts().to_dict() == {
        "Core Ideas": 57,
        "Practices": 25,
    }
    assert not learning_outcomes["LO_ID"].astype(str).str.contains(r"-V\d+$", regex=True).any()
    assert learning_outcomes["LO_ID"].is_unique
    assert learning_outcomes["Topic_Code"].isin(topics["Topic_Code"]).all()

    bank = load_question_bank()
    assert len(bank) == 371
    assert bank["Question_ID"].is_unique
    assert set(bank["Review_Status"]) == {"Approved"}
    validation = validate_question_bank(bank, learning_outcomes)
    assert validation["Valid"].all(), validation[~validation["Valid"]].to_dict(orient="records")
    assert set(learning_outcomes["LO_ID"]) == set(bank["LO_ID"])


def test_password_hash_roundtrip_and_two_account_auth_config():
    teacher_hash = hash_password("correct horse battery staple", salt=b"0123456789abcdef", iterations=10_000)
    admin_hash = hash_password("another secure password", salt=b"fedcba9876543210", iterations=10_000)
    assert verify_password("correct horse battery staple", teacher_hash)
    assert not verify_password("wrong", teacher_hash)

    accounts = accounts_from_auth_config({
        "teacher": {"display_name": "Teacher", "password_hash": teacher_hash},
        "admin": {"display_name": "Admin", "password_hash": admin_hash},
    })
    assert set(accounts) == {"teacher", "admin"}

    teacher = authenticate_account("teacher", "correct horse battery staple", accounts)
    admin = authenticate_account("admin", "another secure password", accounts)
    assert teacher is not None and teacher.role == "teacher"
    assert admin is not None and admin.role == "admin"
    assert authenticate_account("teacher", "wrong", accounts) is None
    assert authenticate_account("alice", "correct horse battery staple", accounts) is None


def _sample_bank():
    rows = []
    for i in range(3):
        row = {col: "" for col in QUESTION_BANK_COLUMNS}
        row.update({
            "Question_ID": f"Q{i+1}",
            "Question_Version": "1",
            "Level": "P3",
            "Topic_Code": "TOPIC",
            "LO_ID": "LO",
            "Question_Text": f"Question {i+1}",
            "Option_A": "A1",
            "Option_B": "B1",
            "Option_C": "C1",
            "Option_D": "D1",
            "Correct_Option": "A",
            "Probe_Type": "Direct concept",
            "Diagnostic_Use": "Any",
            "Review_Status": "Candidate",
        })
        rows.append(row)
    return normalize_question_bank(pd.DataFrame(rows))


def test_question_deletion_is_explicit_and_delete_all_keeps_schema():
    bank = _sample_bank()
    out = delete_questions(bank, ["Q1", "Q3"])
    assert out["Question_ID"].tolist() == ["Q2"]
    assert len(bank) == 3  # helper does not mutate caller

    empty = delete_all_questions(bank)
    assert empty.empty
    assert list(empty.columns) == QUESTION_BANK_COLUMNS


def test_state_snapshot_excludes_oauth_and_static_curriculum(tmp_path):
    # Recreate the mutable paths expected by persistence relative to a project root.
    (tmp_path / "data/question_bank").mkdir(parents=True)
    (tmp_path / "data/reference").mkdir(parents=True)
    (tmp_path / "private_data/google_forms").mkdir(parents=True)
    (tmp_path / "private_data/responses").mkdir(parents=True)
    (tmp_path / "private_data/google_auth").mkdir(parents=True)
    (tmp_path / "output/diagnostics").mkdir(parents=True)

    (tmp_path / "data/question_bank/master_question_bank.csv").write_text("Question_ID\nQ1\n", encoding="utf-8")
    (tmp_path / "data/reference/classes.csv").write_text("Class_Code\nP3A\n", encoding="utf-8")
    (tmp_path / "data/reference/concept_master.xlsx").write_bytes(b"STATIC")
    (tmp_path / "private_data/google_forms/F1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "private_data/responses/F1.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "private_data/google_auth/token.json").write_text("SECRET", encoding="utf-8")
    (tmp_path / "output/diagnostics/x.txt").write_text("output", encoding="utf-8")

    data = build_state_snapshot(tmp_path)
    with zipfile.ZipFile(BytesIO(data)) as z:
        names = set(z.namelist())
    assert "data/question_bank/master_question_bank.csv" in names
    assert "data/reference/classes.csv" in names
    assert "private_data/google_forms/F1.json" in names
    assert "private_data/responses/F1.csv" in names
    assert "output/diagnostics/x.txt" in names
    assert "private_data/google_auth/token.json" not in names
    assert "data/reference/concept_master.xlsx" not in names

    restore_root = tmp_path / "restore"
    # build_state_snapshot relies on config-relative mutable paths; restore has the same relative structure.
    (restore_root / "data/question_bank").mkdir(parents=True)
    (restore_root / "data/reference").mkdir(parents=True)
    (restore_root / "private_data/google_forms").mkdir(parents=True)
    (restore_root / "private_data/responses").mkdir(parents=True)
    (restore_root / "output").mkdir(parents=True)
    restored = restore_state_snapshot(data, restore_root)
    assert "data/question_bank/master_question_bank.csv" in restored
    assert (restore_root / "private_data/google_forms/F1.json").exists()


def test_v250_ui_and_security_contracts():
    app = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    qbank = (ROOT / "app/pages/Question_Bank.py").read_text(encoding="utf-8")
    css = (ROOT / "src/ui.py").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    deployment = (ROOT / "app/pages/Deployment.py").read_text(encoding="utf-8")

    assert "_require_login()" in app
    assert "authenticate_account(account_type, password, accounts)" in app
    assert 'st.Page("pages/Deployment.py"' in app
    assert "hydrate_persistent_state_once()" in app
    assert '"Select All"' in qbank
    assert '"Deselect All"' in qbank
    assert '"Delete Selected"' in qbank
    assert '"Delete All"' in qbank
    assert 'delete_phrase != "DELETE ALL"' in qbank
    assert "@media (max-width: 1024px)" in css
    assert ".streamlit/secrets.toml" in gitignore
    assert "Download state backup" in deployment
