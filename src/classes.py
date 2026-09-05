from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# V2.5.2 class master is deliberately timeless. Admin maintains only Level,
# Class_Name and whether the class is Active. Pupil counts belong to individual
# diagnostic assignments and are entered by the teacher at launch time.
CLASS_COLUMNS = ["Level", "Class_Name", "Active"]
CSV_IMPORT_COLUMNS = CLASS_COLUMNS.copy()


def _clean_code(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip().upper()).strip("_")


def _clean_class_name(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return text.title() if text else ""


def generate_class_key(*args) -> str:
    """Generate the hidden internal class identifier.

    Current use: generate_class_key(level, class_name) -> P3_UNITY.
    A legacy three-argument call (year, level, class_name) is accepted and the
    year is ignored so old modules/data can migrate cleanly.
    """
    if len(args) == 2:
        level, class_name = args
    elif len(args) == 3:
        _, level, class_name = args
    else:
        raise TypeError("generate_class_key expects (level, class_name).")
    return "_".join(part for part in [_clean_code(level), _clean_code(class_name)] if part)


# Backward-compatible alias used by older tests/modules.
def generate_class_code(*args) -> str:
    return generate_class_key(*args)


def class_display_name(row_or_level, class_name: str | None = None) -> str:
    if class_name is None:
        row = row_or_level
        level = str(row.get("Level", "")).strip().upper()
        name = str(row.get("Class_Name", "")).strip()
    else:
        level = str(row_or_level or "").strip().upper()
        name = str(class_name or "").strip()
    return f"{level} {name}".strip()


def class_key_from_row(row) -> str:
    return generate_class_key(row.get("Level", ""), row.get("Class_Name", ""))


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"false", "0", "no", "n", ""}


def normalize_classes(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Return the timeless class-master schema.

    Legacy CSVs with Year, Class_Code, enrolment or index-range fields are
    accepted; those fields are ignored. The current master stores only:
    Level, Class_Name and Active.
    """
    if frame is None or frame.empty:
        return pd.DataFrame(columns=CLASS_COLUMNS)

    result = frame.copy()
    rename = {}
    for column in result.columns:
        key = str(column).strip().casefold().replace(" ", "_")
        if key in {"level", "primary_level"}:
            rename[column] = "Level"
        elif key in {"class_name", "class", "name"}:
            rename[column] = "Class_Name"
        elif key in {"active", "is_active"}:
            rename[column] = "Active"
    result = result.rename(columns=rename)

    for column in CLASS_COLUMNS:
        if column not in result.columns:
            result[column] = True if column == "Active" else ""

    result["Level"] = result["Level"].fillna("").astype(str).str.strip().str.upper()
    result["Class_Name"] = result["Class_Name"].map(_clean_class_name)
    result["Active"] = result["Active"].map(_as_bool)

    meaningful = result["Level"].ne("") | result["Class_Name"].ne("")
    return result.loc[meaningful, CLASS_COLUMNS].reset_index(drop=True)


def validate_classes(frame: pd.DataFrame) -> list[str]:
    classes = normalize_classes(frame)
    errors: list[str] = []
    if classes.empty:
        return errors

    keys: list[str] = []
    for i, row in classes.iterrows():
        label = class_display_name(row) or f"row {i + 1}"
        if not re.fullmatch(r"P[3-6]", str(row["Level"])):
            errors.append(f"{label}: Level must be P3, P4, P5 or P6.")
        if not str(row["Class_Name"]).strip():
            errors.append(f"row {i + 1}: Class name is required.")
        keys.append(class_key_from_row(row) if row["Level"] and row["Class_Name"] else "")

    duplicate_keys = [key for key in keys if key and keys.count(key) > 1]
    if duplicate_keys:
        errors.append(
            "Duplicate level/class combinations: " + ", ".join(sorted(set(duplicate_keys)))
        )
    return errors


def load_classes(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=CLASS_COLUMNS)
    return normalize_classes(pd.read_csv(path, dtype=str).fillna(""))


def save_classes(frame: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    classes = normalize_classes(frame)
    errors = validate_classes(classes)
    if errors:
        raise ValueError("\n".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    classes.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def active_classes_for_level(frame: pd.DataFrame, level: str, year=None) -> pd.DataFrame:
    """Return active classes for a level. `year` is ignored for legacy callers."""
    classes = normalize_classes(frame)
    mask = classes["Active"] & classes["Level"].eq(str(level).upper())
    return classes.loc[mask].sort_values(["Level", "Class_Name"]).reset_index(drop=True)


def active_years(frame: pd.DataFrame) -> list[int]:
    """Legacy compatibility: the current class master has no year dimension."""
    return []


def replace_classes_from_upload(existing: pd.DataFrame, uploaded: pd.DataFrame) -> pd.DataFrame:
    """Replace the current class master with a validated uploaded list."""
    incoming = normalize_classes(uploaded)
    errors = validate_classes(incoming)
    if errors:
        raise ValueError("\n".join(errors))
    if incoming.empty:
        raise ValueError("The uploaded CSV contains no classes.")
    return incoming.reset_index(drop=True)


def replace_years_from_upload(existing: pd.DataFrame, uploaded: pd.DataFrame) -> pd.DataFrame:
    """Backward-compatible alias; years no longer exist, so upload replaces all rows."""
    return replace_classes_from_upload(existing, uploaded)


def make_class_import_template() -> bytes:
    template = pd.DataFrame(
        [
            {"Level": "P3", "Class_Name": "Empathy", "Active": True},
            {"Level": "P3", "Class_Name": "Integrity", "Active": True},
        ],
        columns=CSV_IMPORT_COLUMNS,
    )
    return template.to_csv(index=False).encode("utf-8-sig")


def ensure_default_classes(master_path=None, template_path=None):
    """Ensure the bundled 24-class P3-P6 default exists and migrate older schemas."""
    from .config import CLASSES_PATH, DEFAULT_CLASSES_TEMPLATE_PATH

    master_path = Path(master_path or CLASSES_PATH)
    template_path = Path(template_path or DEFAULT_CLASSES_TEMPLATE_PATH)
    baseline = normalize_classes(pd.read_csv(template_path, dtype=str).fillna(""))
    if len(baseline) != 24:
        raise ValueError("Bundled class master must contain exactly 24 classes.")

    if not master_path.exists():
        save_classes(baseline, master_path)
        return True, "Loaded the bundled 24-class P3-P6 class master."

    try:
        raw = pd.read_csv(master_path, dtype=str).fillna("")
    except Exception:
        raw = pd.DataFrame()

    if raw.empty:
        # An empty current-format class list is an intentional Admin choice.
        if set(CLASS_COLUMNS).issubset(raw.columns):
            return False, "Class master is ready."
        save_classes(baseline, master_path)
        return True, "Restored the bundled 24-class P3-P6 class master."

    legacy_columns = {
        "Year", "Class_Code", "Index_Min", "Index_Max", "Enrolment", "Enrollment",
        "Student_Count", "Students",
    }
    if legacy_columns.intersection(set(raw.columns)) or list(raw.columns) != CLASS_COLUMNS:
        migrated = normalize_classes(raw)
        # Dropping Year can collapse repeated annual copies. Keep one current row
        # per Level + Class_Name, preferring the last stored version.
        migrated = migrated.drop_duplicates(["Level", "Class_Name"], keep="last").reset_index(drop=True)
        if migrated.empty:
            migrated = baseline
        save_classes(migrated, master_path)
        return True, "Migrated the class master to Level/Class Name/Active only."

    return False, "Class master is ready."


# Old runtime code imported this name in earlier RCs.
def ensure_default_2026_classes(master_path=None, template_path=None):
    return ensure_default_classes(master_path=master_path, template_path=template_path)
