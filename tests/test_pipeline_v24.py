import pandas as pd

from src.forms import reaudit_responses_by_manifest, api_responses_wide_to_long, option_text_to_letter
from src.privacy import anonymise_student_data
from src.scoring import score_responses, student_lo_summary


def _bank():
    return pd.DataFrame([
        {
            "Question_ID":"Q1","Level":"P3","Topic_Code":"T1","LO_ID":"L1",
            "Question_Text":"Living?","Option_A":"Rock","Option_B":"Tree","Option_C":"Cup","Option_D":"Spoon",
            "Correct_Option":"B","Answer_Explanation":"","Probe_Type":"Direct concept",
            "TLG_Key_Idea_Ref":"","Alternative_Conception_Ref":"",
        },
        {
            "Question_ID":"Q2","Level":"P3","Topic_Code":"T2","LO_ID":"L2",
            "Question_Text":"Magnetic?","Option_A":"Iron","Option_B":"Glass","Option_C":"Rubber","Option_D":"Plastic",
            "Correct_Option":"A","Answer_Explanation":"","Probe_Type":"Direct concept",
            "TLG_Key_Idea_Ref":"","Alternative_Conception_Ref":"",
        },
    ])


def test_two_classes_same_index_remain_separate_through_scoring():
    wide = pd.DataFrame([
        {
            "Response_ID":"RA","Timestamp":"2026-08-30T10:00:00Z","Form_ID":"FA","Class_Code":"P3A","Class_Name":"3 A","Level":"P3","Index_Number":"17",
            "Q1":"Tree","Q2":"Iron",
        },
        {
            "Response_ID":"RB","Timestamp":"2026-08-30T10:01:00Z","Form_ID":"FB","Class_Code":"P3B","Class_Name":"3 B","Level":"P3","Index_Number":"17",
            "Q1":"Rock","Q2":"Iron",
        },
    ])
    manifests = [
        {"form_id":"FA","index_min":1,"index_max":41},
        {"form_id":"FB","index_min":1,"index_max":41},
    ]
    audited = reaudit_responses_by_manifest(wide, manifests)
    assert not audited["Needs_Review"].any()
    assert set(audited["Pupil_Key"]) == {"P3A_17", "P3B_17"}

    long_frames = []
    for _, group in audited.groupby("Form_ID"):
        long_frames.append(api_responses_wide_to_long(group, ["Q1", "Q2"]))
    long = pd.concat(long_frames, ignore_index=True)
    long = option_text_to_letter(long, _bank())
    scored = score_responses(long, _bank())

    by_pupil = scored.groupby("Pupil_Key")["Correct"].sum().to_dict()
    assert by_pupil == {"P3A_17": 2, "P3B_17": 1}


def test_anonymised_summary_has_no_local_class_or_index_identity():
    scored = pd.DataFrame([
        {
            "Response_ID":"RA","Class_Code":"P3A","Class_Name":"3 A","Index_Number":"17","Pupil_Key":"P3A_17",
            "Level":"P3","Topic_Code":"T1","LO_ID":"L1","Question_ID":"Q1","Correct":True,"Misconception_Linked_Error":False,
        }
    ])
    summary = student_lo_summary(scored)
    anon = anonymise_student_data(summary)
    assert "Anonymous_Response_ID" in anon.columns
    for col in ["Response_ID","Class_Code","Class_Name","Index_Number","Pupil_Key"]:
        assert col not in anon.columns
