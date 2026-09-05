from io import BytesIO
import zipfile

import pandas as pd

from src.config import QUESTION_BANK_COLUMNS
from src.question_bank import (
    make_gemini_notebook_template_pack,
    make_question_bank_template_csv,
    normalize_question_bank,
    prepare_imported_question_bank,
    validate_question_bank,
)


def _lo():
    return pd.DataFrame([
        {
            "LO_ID": "P3-DIV-LNL-C01",
            "Topic_Code": "P3-DIV-LNL",
            "Level": "P3",
            "Theme": "Diversity",
            "Official Topic": "Living and Non-Living Things",
            "Official Domain": "Core Ideas",
            "Official Learning Outcome": "Describe characteristics of living things.",
            "Official Details / Sub-points": "",
        },
        {
            "LO_ID": "P3-INT-MAG-C02",
            "Topic_Code": "P3-INT-MAG",
            "Level": "P3",
            "Theme": "Interactions",
            "Official Topic": "Magnets",
            "Official Domain": "Core Ideas",
            "Official Learning Outcome": "Identify characteristics of magnets.",
            "Official Details / Sub-points": "",
        },
    ])


def _valid_row(**overrides):
    row = {c: "" for c in QUESTION_BANK_COLUMNS}
    row.update({
        "Question_ID": "Q1",
        "Question_Version": "1",
        "Level": "P3",
        "Topic_Code": "P3-DIV-LNL",
        "LO_ID": "P3-DIV-LNL-C01",
        "Question_Text": "Which is living?",
        "Option_A": "Rock",
        "Option_B": "Tree",
        "Option_C": "Spoon",
        "Option_D": "Cup",
        "Correct_Option": "B",
        "Answer_Explanation": "A tree is living.",
        "Probe_Type": "Direct concept",
        "Diagnostic_Use": "Any",
        "Review_Status": "Candidate",
        "Times_Used": "0",
    })
    row.update(overrides)
    return row


def test_blank_editor_rows_are_dropped():
    rows = [_valid_row(), {c: "" for c in QUESTION_BANK_COLUMNS}]
    out = normalize_question_bank(pd.DataFrame(rows))
    assert len(out) == 1
    assert out.loc[0, "Question_ID"] == "Q1"


def test_import_defaults_and_assigns_id():
    row = _valid_row(Question_ID="", Review_Status="", Diagnostic_Use="", Question_Version="", Created_Date="")
    out = prepare_imported_question_bank(pd.DataFrame([row]))
    assert out.loc[0, "Question_ID"].startswith("P3DQ")
    assert out.loc[0, "Review_Status"] == "Candidate"
    assert out.loc[0, "Diagnostic_Use"] == "Any"
    assert out.loc[0, "Question_Version"] == "1"
    assert out.loc[0, "Created_Date"]


def test_valid_question_passes_schema_and_concept_master():
    result = validate_question_bank(pd.DataFrame([_valid_row()]), _lo())
    assert bool(result.loc[0, "Valid"])
    assert result.loc[0, "Problems"] == ""


def test_unknown_diagnostic_use_is_caught_before_create_page():
    result = validate_question_bank(pd.DataFrame([_valid_row(Diagnostic_Use="System Test")]), _lo())
    assert not bool(result.loc[0, "Valid"])
    assert "Unknown Diagnostic_Use" in result.loc[0, "Problems"]


def test_topic_and_level_must_match_lo_id():
    result = validate_question_bank(
        pd.DataFrame([_valid_row(Topic_Code="P3-INT-MAG", Level="P4")]),
        _lo(),
    )
    problems = result.loc[0, "Problems"]
    assert "Level does not match LO_ID" in problems
    assert "Topic_Code does not match LO_ID" in problems


def test_duplicate_option_text_is_rejected_case_insensitively():
    result = validate_question_bank(pd.DataFrame([_valid_row(Option_D="rock")]), _lo())
    assert not bool(result.loc[0, "Valid"])
    assert "Options A-D must have distinct text" in result.loc[0, "Problems"]


def test_blank_template_has_exact_import_columns():
    template = pd.read_csv(BytesIO(make_question_bank_template_csv()))
    assert list(template.columns) == QUESTION_BANK_COLUMNS
    assert template.empty


def test_gemini_notebook_template_pack_is_self_documenting():
    topics = _lo()[["Topic_Code", "Level", "Theme", "Official Topic"]].drop_duplicates()
    blob = make_gemini_notebook_template_pack(_lo(), topics)
    with zipfile.ZipFile(BytesIO(blob)) as z:
        names = set(z.namelist())
        assert names == {
            "question_bank_template.csv",
            "learning_outcome_reference.csv",
            "topic_reference.csv",
            "valid_values_reference.csv",
            "GEMINI_NOTEBOOK_INSTRUCTIONS.txt",
        }
        instructions = z.read("GEMINI_NOTEBOOK_INSTRUCTIONS.txt").decode("utf-8")
        assert "Do not invent curriculum content, LO_IDs" in instructions
        valid_values = pd.read_csv(z.open("valid_values_reference.csv"))
        assert "Diagnostic_Use" in set(valid_values["Field"])


def test_teacher_moderation_helpers_update_status_and_approval_date():
    from src.question_bank import set_question_review_status, update_question_record

    bank = pd.DataFrame([_valid_row()])
    approved = set_question_review_status(bank, "Q1", "Approved")
    assert approved.loc[0, "Review_Status"] == "Approved"
    assert approved.loc[0, "Approved_Date"]

    edited = update_question_record(approved, "Q1", {"Question_Text": "Which one is living?"})
    assert edited.loc[0, "Question_ID"] == "Q1"
    assert edited.loc[0, "Question_Text"] == "Which one is living?"

    rejected = set_question_review_status(edited, "Q1", "Rejected")
    assert rejected.loc[0, "Review_Status"] == "Rejected"
    assert rejected.loc[0, "Approved_Date"] == ""


def test_prepare_multiple_imports_assigns_unique_ids_across_files():
    from src.question_bank import prepare_multiple_imports

    first = pd.DataFrame([_valid_row(Question_ID="", Question_Text="First question")])
    second = pd.DataFrame([_valid_row(Question_ID="", Question_Text="Second question")])
    out = prepare_multiple_imports([first, second])
    assert len(out) == 2
    assert out["Question_ID"].nunique() == 2
    assert all(qid.startswith("P3DQ") for qid in out["Question_ID"])


def test_bulk_approval_sets_status_and_date_for_several_questions():
    from src.question_bank import set_questions_review_status

    bank = pd.DataFrame([
        _valid_row(Question_ID="Q1"),
        _valid_row(Question_ID="Q2", Question_Text="Which one grows?"),
    ])
    out = set_questions_review_status(bank, ["Q1", "Q2"], "Approved")
    assert set(out["Review_Status"]) == {"Approved"}
    assert out["Approved_Date"].ne("").all()


def test_merge_imports_preserves_existing_teacher_record_by_default():
    from src.question_bank import merge_imported_questions

    existing = pd.DataFrame([_valid_row(Question_ID="Q1", Question_Text="Teacher edited wording")])
    incoming = pd.DataFrame([
        _valid_row(Question_ID="Q1", Question_Text="Old imported wording"),
        _valid_row(Question_ID="Q2", Question_Text="New question"),
    ])
    out = merge_imported_questions(existing, incoming)
    assert len(out) == 2
    assert out.loc[out["Question_ID"].eq("Q1"), "Question_Text"].iloc[0] == "Teacher edited wording"
    assert "Q2" in set(out["Question_ID"])
