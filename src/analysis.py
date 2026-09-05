import pandas as pd

def add_curriculum_wording(student_lo, learning_outcomes):
    cols = [
        "LO_ID",
        "Official Topic",
        "Official Learning Outcome",
        "Official Details / Sub-points",
    ]

    lookup = learning_outcomes[cols].drop_duplicates("LO_ID")

    return student_lo.merge(
        lookup,
        on="LO_ID",
        how="left",
        validate="many_to_one",
    )

def add_optional_evidence_labels(summary, analysis_config):
    '''
    Labels are deliberately optional because the project has not yet
    calibrated mastery thresholds using pilot data.
    '''
    result = summary.copy()

    if not analysis_config.get("use_mastery_labels", False):
        result["Evidence_Label"] = ""
        return result

    secure = analysis_config["pilot_thresholds"]["secure_percent"]
    developing = analysis_config["pilot_thresholds"]["developing_percent"]
    minimum = analysis_config["minimum_evidence"]["minimum_questions_per_lo_for_label"]

    def label(row):
        if row["Questions"] < minimum:
            return "Insufficient evidence"
        if row["Percent_Correct"] >= secure:
            return "Stronger evidence"
        if row["Percent_Correct"] >= developing:
            return "Developing evidence"
        return "Priority for review"

    result["Evidence_Label"] = result.apply(label, axis=1)
    return result

def rank_class_revision_priorities(class_lo):
    result = class_lo.copy()
    result["Incorrect"] = result["Responses"] - result["Correct"]
    return result.sort_values(
        ["Percent_Correct", "Misconception_Linked_Errors", "Responses"],
        ascending=[True, False, False],
    ).reset_index(drop=True)
