import pandas as pd

from src.classes import normalize_classes, validate_classes
from src.diagnostic import select_balanced_questions
from src.forms import normalize_index_number, make_pupil_key, audit_index_numbers, api_responses_wide_to_long
from src.privacy import anonymise_student_data, strip_local_pupil_identity
from src.scoring import score_responses


def test_balanced_selection_covers_learning_outcomes():
    pool = pd.DataFrame([
        {"Question_ID":"Q1","LO_ID":"L1","Times_Used":0},
        {"Question_ID":"Q2","LO_ID":"L1","Times_Used":0},
        {"Question_ID":"Q3","LO_ID":"L2","Times_Used":0},
        {"Question_ID":"Q4","LO_ID":"L2","Times_Used":0},
    ])
    selected = select_balanced_questions(pool, 2, seed=1)
    assert set(selected["LO_ID"]) == {"L1", "L2"}


def test_index_number_normalisation():
    assert normalize_index_number(" 017 ") == "17"
    assert normalize_index_number("17.0") == "17"
    assert normalize_index_number("abc") == ""


def test_pupil_key_separates_same_index_across_classes():
    assert make_pupil_key("P3UNITY", 17) == "P3UNITY_17"
    assert make_pupil_key("P3WONDER", 17) == "P3WONDER_17"
    assert make_pupil_key("P3UNITY", 17) != make_pupil_key("P3WONDER", 17)


def test_duplicate_submission_is_flagged_within_class():
    responses = pd.DataFrame([
        {"Response_ID":"R1", "Class_Code":"P3U", "Class_Name":"3 Unity", "Index_Number":"7"},
        {"Response_ID":"R2", "Class_Code":"P3U", "Class_Name":"3 Unity", "Index_Number":"07"},
        {"Response_ID":"R3", "Class_Code":"P3U", "Class_Name":"3 Unity", "Index_Number":"8"},
    ])
    audit = audit_index_numbers(responses, 1, 41)
    duplicate = audit[audit["Pupil_Key"].eq("P3U_07")]
    assert len(duplicate) == 2
    assert duplicate["Needs_Review"].all()
    assert not bool(audit.loc[audit["Response_ID"].eq("R3"), "Needs_Review"].iloc[0])


def test_out_of_range_index_is_flagged():
    responses = pd.DataFrame([{
        "Response_ID":"R1", "Class_Code":"P3U", "Class_Name":"3 Unity", "Index_Number":"42"
    }])
    audit = audit_index_numbers(responses, 1, 41)
    assert not bool(audit.loc[0, "Index_In_Range"])
    assert bool(audit.loc[0, "Needs_Review"])


def test_api_wide_to_long_keeps_class_and_index():
    wide = pd.DataFrame([{
        "Response_ID":"G1", "Timestamp":"2026-08-30T08:00:00Z",
        "Class_Code":"P3U", "Class_Name":"3 Unity", "Index_Number":"17", "Pupil_Key":"P3U_17",
        "Q1":"Attract", "Q2":"Repel",
    }])
    long = api_responses_wide_to_long(wide, ["Q1", "Q2"])
    assert set(long["Question_ID"]) == {"Q1", "Q2"}
    assert set(long["Class_Name"]) == {"3 Unity"}
    assert set(long["Pupil_Key"]) == {"P3U_17"}


def test_score_responses_v24():
    responses = pd.DataFrame([{
        "Response_ID":"R1", "Class_Code":"P3U", "Class_Name":"3 Unity",
        "Index_Number":"17", "Pupil_Key":"P3U_17", "Question_ID":"Q1", "Student_Response":"A"
    }])
    bank = pd.DataFrame([{
        "Question_ID":"Q1", "Level":"P3", "Topic_Code":"T", "LO_ID":"L1",
        "Correct_Option":"A", "Probe_Type":"Direct concept", "Alternative_Conception_Ref":"",
    }])
    scored = score_responses(responses, bank)
    assert bool(scored.loc[0, "Correct"])


def test_anonymise_removes_local_pupil_identity():
    df = pd.DataFrame([{
        "Response_ID":"R1", "Pupil_Key":"P3U_17", "Class_Code":"P3U", "Class_Name":"3 Unity",
        "Index_Number":"17", "Timestamp":"2026-08-30", "LO_ID":"L1"
    }])
    anon = anonymise_student_data(df)
    for col in ["Response_ID", "Pupil_Key", "Class_Code", "Class_Name", "Index_Number", "Timestamp"]:
        assert col not in anon.columns
    assert anon.loc[0, "Anonymous_Response_ID"].startswith("ANON-")


def test_strip_identity_for_gemini():
    df = pd.DataFrame([{
        "Response_ID":"R1", "Pupil_Key":"P3U_17", "Class_Code":"P3U", "Class_Name":"3 Unity",
        "Index_Number":"17", "Question_ID":"Q1"
    }])
    stripped = strip_local_pupil_identity(df)
    assert list(stripped.columns) == ["Question_ID"]


def test_class_config_validation():
    classes = normalize_classes(pd.DataFrame([{
        "Year": 2026, "Class_Name":"Unity", "Level":"p3", "Active":True,
    }]))
    assert list(classes.columns) == ["Level", "Class_Name", "Active"]
    assert classes.loc[0, "Class_Name"] == "Unity"
    assert classes.loc[0, "Level"] == "P3"
    assert validate_classes(classes) == []


def test_reaudit_after_excluding_duplicate_clears_remaining_copy():
    from src.forms import reaudit_responses_by_manifest

    responses = pd.DataFrame([
        {"Response_ID":"R1", "Form_ID":"F1", "Class_Code":"P3U", "Class_Name":"3 Unity", "Index_Number":"7"},
        {"Response_ID":"R2", "Form_ID":"F1", "Class_Code":"P3U", "Class_Name":"3 Unity", "Index_Number":"07"},
    ])
    manifests = [{"form_id":"F1", "index_min":1, "index_max":41}]
    first = reaudit_responses_by_manifest(responses, manifests)
    assert first["Needs_Review"].all()

    remaining = first[first["Response_ID"].eq("R1")].copy()
    second = reaudit_responses_by_manifest(remaining, manifests)
    assert len(second) == 1
    assert not bool(second.loc[0, "Needs_Review"])


def test_reaudit_uses_each_forms_own_index_range():
    from src.forms import reaudit_responses_by_manifest

    responses = pd.DataFrame([
        {"Response_ID":"R1", "Form_ID":"F1", "Class_Code":"P3U", "Class_Name":"3 Unity", "Index_Number":"40"},
        {"Response_ID":"R2", "Form_ID":"F2", "Class_Code":"P3W", "Class_Name":"3 Wonder", "Index_Number":"40"},
    ])
    manifests = [
        {"form_id":"F1", "index_min":1, "index_max":41},
        {"form_id":"F2", "index_min":1, "index_max":35},
    ]
    audit = reaudit_responses_by_manifest(responses, manifests)
    assert not bool(audit.loc[audit["Form_ID"].eq("F1"), "Needs_Review"].iloc[0])
    assert bool(audit.loc[audit["Form_ID"].eq("F2"), "Needs_Review"].iloc[0])
