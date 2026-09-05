from io import BytesIO
import zipfile

import pandas as pd

from src.diagnostic import (
    build_diagnostic_package,
    eligible_questions,
    scope_filter_audit,
)


def _bank():
    return pd.DataFrame([
        {"Question_ID":"Q1","Review_Status":"Approved","Level":"P3","Topic_Code":"T1","LO_ID":"L1","Diagnostic_Use":"Any","Times_Used":0,
         "Question_Text":"Q1?","Option_A":"A1","Option_B":"B1","Option_C":"C1","Option_D":"D1","Correct_Option":"A","Answer_Explanation":"","Probe_Type":"Direct concept","Alternative_Conception_Ref":"","Source_Note":"","TLG_Key_Idea_Ref":""},
        {"Question_ID":"Q2","Review_Status":"Approved","Level":"P3","Topic_Code":"T1","LO_ID":"L2","Diagnostic_Use":"EOY","Times_Used":0,
         "Question_Text":"Q2?","Option_A":"A2","Option_B":"B2","Option_C":"C2","Option_D":"D2","Correct_Option":"B","Answer_Explanation":"","Probe_Type":"Application","Alternative_Conception_Ref":"","Source_Note":"","TLG_Key_Idea_Ref":""},
        {"Question_ID":"Q3","Review_Status":"Candidate","Level":"P3","Topic_Code":"T1","LO_ID":"L3","Diagnostic_Use":"Any","Times_Used":0,
         "Question_Text":"Q3?","Option_A":"A3","Option_B":"B3","Option_C":"C3","Option_D":"D3","Correct_Option":"C","Answer_Explanation":"","Probe_Type":"Direct concept","Alternative_Conception_Ref":"","Source_Note":"","TLG_Key_Idea_Ref":""},
    ])


def test_any_questions_are_eligible_for_each_diagnostic_type():
    bank = _bank()
    for kind in ["Topic", "Pre-WA", "EOY"]:
        pool = eligible_questions(bank, "P3", ["T1"], kind)
        assert "Q1" in set(pool["Question_ID"])
    assert set(eligible_questions(bank, "P3", ["T1"], "EOY")["Question_ID"]) == {"Q1", "Q2"}


def test_scope_filter_audit_explains_diagnostic_use_mismatch():
    audit = scope_filter_audit(_bank(), "P3", ["T1"], "Pre-WA")
    assert audit["approved_at_level"] == 2
    assert audit["approved_at_topics"] == 2
    assert audit["eligible"] == 1
    assert set(audit["available_diagnostic_uses"]) == {"Any", "EOY"}


def test_diagnostic_package_uses_explicit_diagnostic_id_and_expected_files():
    selected = _bank().iloc[[0]].copy()
    blob, metadata = build_diagnostic_package(selected, "Demo", diagnostic_id="P3_Topic_TEST")
    assert metadata["diagnostic_id"] == "P3_Topic_TEST"
    with zipfile.ZipFile(BytesIO(blob)) as z:
        assert set(z.namelist()) == {
            "student_questions.csv",
            "answer_key.csv",
            "diagnostic_blueprint.csv",
            "google_forms_ready.csv",
            "diagnostic_manifest.json",
        }
        student = pd.read_csv(z.open("student_questions.csv"))
        assert student.loc[0, "Question_ID"] == "Q1"


def test_comprehensive_audit_checks_official_learning_outcomes_and_tags():
    from src.diagnostic import comprehensive_coverage_audit

    selected = pd.DataFrame([
        {"Question_ID":"Q1","LO_ID":"L1","TLG_Key_Idea_Ref":"KI1","Alternative_Conception_Ref":"AC1"},
        {"Question_ID":"Q2","LO_ID":"L1","TLG_Key_Idea_Ref":"KI2","Alternative_Conception_Ref":""},
    ])
    learning_outcomes = pd.DataFrame([
        {"Level":"P3","Topic_Code":"T1","LO_ID":"L1","Official Domain":"Core Ideas","Official Learning Outcome":"LO one","Official Details / Sub-points":"a"},
        {"Level":"P3","Topic_Code":"T1","LO_ID":"L2","Official Domain":"Practices","Official Learning Outcome":"LO two","Official Details / Sub-points":"b"},
    ])
    audit = comprehensive_coverage_audit(selected, learning_outcomes, "P3", ["T1"])
    assert audit["required_lo_count"] == 2
    assert audit["covered_lo_count"] == 1
    assert audit["missing_lo_ids"] == ["L2"]
    assert audit["key_idea_count"] == 2
    assert audit["alternative_conception_count"] == 1
    assert list(audit["official_coverage"]["Approved question count"]) == [2, 0]


def test_cumulative_levels_allow_lower_primary_science_topics():
    from src.diagnostic import cumulative_levels

    assert cumulative_levels("P3") == ["P3"]
    assert cumulative_levels("P4") == ["P3", "P4"]
    assert cumulative_levels("P5") == ["P3", "P4", "P5"]
    assert cumulative_levels("P6") == ["P3", "P4", "P5", "P6"]


def test_eligible_questions_can_mix_lower_levels_for_cumulative_assessment():
    bank = pd.DataFrame([
        {"Question_ID":"P3Q","Review_Status":"Approved","Level":"P3","Topic_Code":"P3T","LO_ID":"P3L","Diagnostic_Use":"Any"},
        {"Question_ID":"P4Q","Review_Status":"Approved","Level":"P4","Topic_Code":"P4T","LO_ID":"P4L","Diagnostic_Use":"Any"},
        {"Question_ID":"P5Q","Review_Status":"Approved","Level":"P5","Topic_Code":"P5T","LO_ID":"P5L","Diagnostic_Use":"Any"},
        {"Question_ID":"P6Q","Review_Status":"Approved","Level":"P6","Topic_Code":"P6T","LO_ID":"P6L","Diagnostic_Use":"Any"},
    ])
    pool = eligible_questions(bank, levels=["P3", "P4", "P5"], topic_codes=["P3T", "P5T"])
    assert set(pool["Question_ID"]) == {"P3Q", "P5Q"}


def test_auto_build_balances_learning_outcomes_before_repeating_them():
    rows = []
    for lo in ["L1", "L2", "L3"]:
        for i, probe in enumerate(["Direct concept", "Application", "Misconception probe"], start=1):
            rows.append({
                "Question_ID": f"{lo}Q{i}", "Review_Status":"Approved", "Level":"P3",
                "Topic_Code":"T1", "LO_ID":lo, "Diagnostic_Use":"Any", "Times_Used":i,
                "Probe_Type":probe, "TLG_Key_Idea_Ref":"", "Alternative_Conception_Ref":"",
            })
    pool = pd.DataFrame(rows)
    from src.diagnostic import select_balanced_questions
    selected = select_balanced_questions(pool, 3, seed=1)
    assert set(selected["LO_ID"]) == {"L1", "L2", "L3"}


def test_comprehensive_auto_build_covers_tags_without_selecting_every_question():
    rows = [
        {"Question_ID":"Q1","LO_ID":"L1","Probe_Type":"Direct concept","Times_Used":0,"TLG_Key_Idea_Ref":"KI1","Alternative_Conception_Ref":""},
        {"Question_ID":"Q2","LO_ID":"L1","Probe_Type":"Application","Times_Used":0,"TLG_Key_Idea_Ref":"KI1","Alternative_Conception_Ref":"AC1"},
        {"Question_ID":"Q3","LO_ID":"L1","Probe_Type":"Misconception probe","Times_Used":0,"TLG_Key_Idea_Ref":"KI2","Alternative_Conception_Ref":""},
        {"Question_ID":"Q4","LO_ID":"L1","Probe_Type":"Other","Times_Used":99,"TLG_Key_Idea_Ref":"KI1","Alternative_Conception_Ref":""},
        {"Question_ID":"Q5","LO_ID":"L2","Probe_Type":"Direct concept","Times_Used":0,"TLG_Key_Idea_Ref":"KI3","Alternative_Conception_Ref":""},
        {"Question_ID":"Q6","LO_ID":"L2","Probe_Type":"Application","Times_Used":0,"TLG_Key_Idea_Ref":"KI3","Alternative_Conception_Ref":"AC2"},
    ]
    pool = pd.DataFrame(rows)
    from src.diagnostic import select_comprehensive_questions
    selected = select_comprehensive_questions(pool, seed=1, minimum_per_lo=2)
    assert set(selected["LO_ID"]) == {"L1", "L2"}
    assert {"KI1", "KI2", "KI3"}.issubset(set(selected["TLG_Key_Idea_Ref"]))
    assert {"AC1", "AC2"}.issubset(set(selected["Alternative_Conception_Ref"]))
    assert len(selected) < len(pool)
