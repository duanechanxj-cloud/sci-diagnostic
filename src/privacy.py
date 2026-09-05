from pathlib import Path
import hashlib
import pandas as pd

DIRECT_ID_COLUMNS = {
    "Student_Name", "Name", "Email Address", "Email", "NRIC", "FIN",
}
LOCAL_PUPIL_COLUMNS = {
    "Response_ID", "Pupil_Key", "Class_Code", "Class_Name", "Index_Number",
    "Index_Number_Raw", "Timestamp", "Internal_Student_Key", "Student_ID",
}


def find_identifiable_columns(df):
    return sorted(set(df.columns) & (DIRECT_ID_COLUMNS | LOCAL_PUPIL_COLUMNS))


def strip_local_pupil_identity(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[c for c in df.columns if c in DIRECT_ID_COLUMNS | LOCAL_PUPIL_COLUMNS], errors="ignore").copy()


def anonymise_student_data(df, id_column="Response_ID"):
    result = df.copy()
    if id_column not in result.columns:
        raise ValueError(f"{id_column} is required for anonymisation.")
    result["Anonymous_Response_ID"] = result[id_column].astype(str).map(
        lambda x: "ANON-" + hashlib.sha256(x.encode("utf-8")).hexdigest()[:10].upper()
    )
    result = strip_local_pupil_identity(result)
    ordered = ["Anonymous_Response_ID"] + [c for c in result.columns if c != "Anonymous_Response_ID"]
    return result[ordered]


def assert_private_path(path, project_root):
    path = Path(path).resolve()
    private_root = (Path(project_root) / "private_data").resolve()
    if private_root not in path.parents and path != private_root:
        raise ValueError("Operational pupil response data should be stored under private_data/.")
    return True
