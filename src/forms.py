import re
import pandas as pd

QID_PATTERN = re.compile(r"\[QID:([^\]]+)\]")


def extract_question_id(header):
    match = QID_PATTERN.search(str(header))
    return match.group(1).strip() if match else None


def normalize_index_number(value) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    if not re.fullmatch(r"\d+", text):
        return ""
    return str(int(text))


def make_pupil_key(class_code: str, index_number) -> str:
    code = re.sub(r"[^A-Za-z0-9]+", "_", str(class_code or "").strip().upper()).strip("_")
    index = normalize_index_number(index_number)
    if not code or not index:
        return ""
    return f"{code}_{int(index):02d}"


def add_internal_response_ids(responses: pd.DataFrame) -> pd.DataFrame:
    result = responses.copy()
    if "Response_ID" not in result.columns:
        result.insert(0, "Response_ID", [f"RESP_{i:04d}" for i in range(1, len(result) + 1)])
    else:
        ids = result["Response_ID"].fillna("").astype(str).str.strip()
        counter = 1
        for idx in result.index[ids.eq("")]:
            ids.loc[idx] = f"RESP_{counter:04d}"
            counter += 1
        result["Response_ID"] = ids
    return result


def audit_index_numbers(
    responses: pd.DataFrame,
    index_min: int = 1,
    index_max: int = 41,
) -> pd.DataFrame:
    result = add_internal_response_ids(responses)
    for col in ["Class_Code", "Class_Name", "Index_Number"]:
        if col not in result.columns:
            raise ValueError(f"{col} is required for index-number auditing.")

    result["Index_Number_Raw"] = result["Index_Number"].fillna("").astype(str).str.strip()
    result["Index_Number"] = result["Index_Number_Raw"].map(normalize_index_number)
    numeric = pd.to_numeric(result["Index_Number"], errors="coerce")
    result["Index_Format_OK"] = numeric.notna()
    result["Index_In_Range"] = numeric.between(int(index_min), int(index_max), inclusive="both")
    result["Pupil_Key"] = [make_pupil_key(c, i) for c, i in zip(result["Class_Code"], result["Index_Number"])]

    valid_key = result["Pupil_Key"].astype(str).str.strip().ne("")
    counts = result.loc[valid_key].groupby("Pupil_Key")["Response_ID"].transform("count")
    result["Duplicate_Submission_Count"] = 0
    result.loc[valid_key, "Duplicate_Submission_Count"] = counts.astype(int)
    result["Needs_Review"] = (
        ~result["Index_Format_OK"]
        | ~result["Index_In_Range"]
        | (result["Duplicate_Submission_Count"] > 1)
    )
    return result


def api_responses_wide_to_long(responses: pd.DataFrame, question_ids: list[str]) -> pd.DataFrame:
    required = {"Response_ID", "Class_Code", "Class_Name", "Index_Number", "Pupil_Key"}
    missing = required - set(responses.columns)
    if missing:
        raise ValueError(f"Missing API response columns: {sorted(missing)}")

    records = []
    for _, row in responses.iterrows():
        for question_id in question_ids:
            record = {
                "Response_ID": str(row["Response_ID"]).strip(),
                "Class_Code": str(row["Class_Code"]).strip(),
                "Class_Name": str(row["Class_Name"]).strip(),
                "Index_Number": normalize_index_number(row["Index_Number"]),
                "Pupil_Key": str(row["Pupil_Key"]).strip(),
                "Question_ID": question_id,
                "Student_Response_Raw": str(row.get(question_id, "")).strip(),
            }
            if "Level" in responses.columns:
                record["Form_Level"] = str(row.get("Level", "")).strip()
            if "Timestamp" in responses.columns:
                record["Timestamp"] = row.get("Timestamp", "")
            records.append(record)
    return pd.DataFrame(records)


def option_text_to_letter(scored_or_responses, question_bank):
    bank = question_bank.set_index("Question_ID")
    result = scored_or_responses.copy()

    def convert(row):
        qid = row["Question_ID"]
        raw = str(row["Student_Response_Raw"]).strip()
        if raw.upper() in {"A", "B", "C", "D"}:
            return raw.upper()
        if qid not in bank.index:
            return ""
        q = bank.loc[qid]
        for letter in ["A", "B", "C", "D"]:
            if raw == str(q[f"Option_{letter}"]).strip():
                return letter
        return ""

    result["Student_Response"] = result.apply(convert, axis=1)
    return result


def google_forms_wide_to_long(*args, **kwargs):
    raise NotImplementedError(
        "V2.4.1 uses the native Google Forms API workflow. Re-fetch the Form from Streamlit instead of importing a legacy named CSV."
    )


def reaudit_responses_by_manifest(responses: pd.DataFrame, manifests: list[dict]) -> pd.DataFrame:
    """Re-run class-specific index/duplicate checks after exclusions.

    This is used before scoring so an accidental duplicate cannot be counted simply
    because the original audit was performed before the teacher excluded one copy.
    """
    if responses.empty:
        return responses.copy()
    if "Form_ID" not in responses.columns:
        raise ValueError("Form_ID is required for class-specific response re-auditing.")

    manifest_by_form = {str(m["form_id"]): m for m in manifests}
    frames = []
    for form_id, group in responses.groupby("Form_ID", sort=False):
        manifest = manifest_by_form.get(str(form_id))
        if not manifest:
            raise ValueError(f"No Form manifest found for Form_ID {form_id}.")
        audited = audit_index_numbers(
            group.copy(),
            int(manifest.get("index_min", 1)),
            int(manifest.get("index_max", 41)),
        )
        audited["Form_ID"] = str(form_id)
        frames.append(audited)
    return pd.concat(frames, ignore_index=True) if frames else responses.iloc[0:0].copy()
