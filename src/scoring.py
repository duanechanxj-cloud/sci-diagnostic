import pandas as pd

IDENTITY_GROUP = ["Response_ID", "Class_Code", "Class_Name", "Index_Number", "Pupil_Key"]


def score_responses(responses_long, question_bank):
    required = {*IDENTITY_GROUP, "Question_ID", "Student_Response"}
    missing = required - set(responses_long.columns)
    if missing:
        raise ValueError(f"Missing response columns: {sorted(missing)}")

    preferred_bank_cols = [
        "Question_ID", "Level", "Topic_Code", "LO_ID", "Question_Text",
        "Option_A", "Option_B", "Option_C", "Option_D", "Correct_Option",
        "Answer_Explanation", "Probe_Type", "TLG_Key_Idea_Ref",
        "Alternative_Conception_Ref",
    ]
    bank_cols = [c for c in preferred_bank_cols if c in question_bank.columns]
    merged = responses_long.merge(
        question_bank[bank_cols], on="Question_ID", how="left", validate="many_to_one"
    )
    if merged["LO_ID"].isna().any():
        missing_qids = merged.loc[merged["LO_ID"].isna(), "Question_ID"].drop_duplicates().tolist()
        raise ValueError(f"Some Question_IDs were not found in the question bank: {missing_qids}")

    merged["Student_Response"] = merged["Student_Response"].astype(str).str.strip().str.upper()
    merged["Correct"] = merged["Student_Response"].eq(merged["Correct_Option"])
    ac = merged.get("Alternative_Conception_Ref", pd.Series("", index=merged.index))
    merged["Misconception_Linked_Error"] = (~merged["Correct"] & ac.astype(str).str.strip().ne(""))
    return merged


def add_curriculum_to_scored(scored, learning_outcomes):
    cols = ["LO_ID", "Official Topic", "Official Learning Outcome", "Official Details / Sub-points"]
    lookup = learning_outcomes[cols].drop_duplicates("LO_ID")
    return scored.merge(lookup, on="LO_ID", how="left", validate="many_to_one")


def student_lo_summary(scored):
    return (
        scored.groupby([*IDENTITY_GROUP, "Level", "Topic_Code", "LO_ID"], dropna=False)
        .agg(
            Questions=("Question_ID", "count"),
            Correct=("Correct", "sum"),
            Misconception_Linked_Errors=("Misconception_Linked_Error", "sum"),
        )
        .reset_index()
        .assign(Percent_Correct=lambda d: (d["Correct"] / d["Questions"] * 100).round(1))
    )


def student_topic_summary(scored):
    return (
        scored.groupby([*IDENTITY_GROUP, "Level", "Topic_Code"], dropna=False)
        .agg(Questions=("Question_ID", "count"), Correct=("Correct", "sum"))
        .reset_index()
        .assign(Percent_Correct=lambda d: (d["Correct"] / d["Questions"] * 100).round(1))
    )


def class_lo_summary(scored):
    return (
        scored.groupby(["Class_Code", "Class_Name", "Level", "Topic_Code", "LO_ID"], dropna=False)
        .agg(
            Responses=("Question_ID", "count"),
            Correct=("Correct", "sum"),
            Students=("Pupil_Key", "nunique"),
            Misconception_Linked_Errors=("Misconception_Linked_Error", "sum"),
        )
        .reset_index()
        .assign(Percent_Correct=lambda d: (d["Correct"] / d["Responses"] * 100).round(1))
    )


def student_question_summary(scored):
    return (
        scored.groupby(IDENTITY_GROUP)
        .agg(Questions=("Question_ID", "count"), Correct=("Correct", "sum"))
        .reset_index()
        .assign(Percent_Correct=lambda d: (d["Correct"] / d["Questions"] * 100).round(1))
    )
