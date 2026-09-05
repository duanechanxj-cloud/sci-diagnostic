from __future__ import annotations

from datetime import date
from io import BytesIO
import zipfile

import pandas as pd

from .config import QUESTION_BANK_PATH, QUESTION_BANK_COLUMNS
from .io_utils import clean_text, write_csv_utf8

VALID_OPTIONS = {"A", "B", "C", "D"}
VALID_STATUSES = {"Candidate", "Approved", "Rejected", "Retired"}
VALID_PROBE_TYPES = {"Direct concept", "Application", "Misconception probe", "Other"}
VALID_DIAGNOSTIC_USES = {"Topic", "Pre-WA", "EOY", "Any"}

AUTHORING_COLUMNS = [
    "Level", "Topic_Code", "LO_ID", "Question_Text",
    "Option_A", "Option_B", "Option_C", "Option_D",
    "Correct_Option", "Answer_Explanation", "Probe_Type",
    "TLG_Key_Idea_Ref", "Alternative_Conception_Ref",
    "Diagnostic_Use", "Source_Note", "Teacher_Notes",
]


def _drop_fully_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove placeholder rows produced by editors without deleting real drafts."""
    if df.empty:
        return df.copy()
    present = [c for c in AUTHORING_COLUMNS if c in df.columns]
    if not present:
        return df.copy()
    meaningful = df[present].fillna("").astype(str).apply(
        lambda col: col.str.strip().ne("")
    ).any(axis=1)
    return df.loc[meaningful].copy()


def normalize_question_bank(df):
    df = _drop_fully_empty_rows(df.copy())

    for col in QUESTION_BANK_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[QUESTION_BANK_COLUMNS]

    for col in QUESTION_BANK_COLUMNS:
        df[col] = df[col].map(clean_text)

    df["Correct_Option"] = df["Correct_Option"].str.upper()
    df["Times_Used"] = pd.to_numeric(df["Times_Used"], errors="coerce").fillna(0).astype(int)

    return df.reset_index(drop=True)


def load_question_bank(path=QUESTION_BANK_PATH):
    if not path.exists():
        return normalize_question_bank(pd.DataFrame(columns=QUESTION_BANK_COLUMNS))
    return normalize_question_bank(pd.read_csv(path, dtype=str).fillna(""))


def save_question_bank(df, path=QUESTION_BANK_PATH):
    df = normalize_question_bank(df)
    today = date.today().isoformat()
    approved = df["Review_Status"].eq("Approved")
    df.loc[approved & df["Approved_Date"].eq(""), "Approved_Date"] = today
    df.loc[~approved, "Approved_Date"] = ""
    df.loc[~approved, "Approved_By"] = ""
    return write_csv_utf8(df, path)


def prepare_imported_question_bank(df, existing_bank=None):
    """Apply safe defaults to a Gemini Notebook-produced CSV before review."""
    df = normalize_question_bank(df)
    if df.empty:
        return df

    today = date.today().isoformat()
    df.loc[df["Question_Version"].eq(""), "Question_Version"] = "1"
    df.loc[df["Diagnostic_Use"].eq(""), "Diagnostic_Use"] = "Any"
    df.loc[df["Review_Status"].eq(""), "Review_Status"] = "Candidate"
    df.loc[df["Created_Date"].eq(""), "Created_Date"] = today
    df = assign_missing_question_ids(df, existing_bank=existing_bank)
    return normalize_question_bank(df)


def validate_question_bank(df, learning_outcomes):
    df = normalize_question_bank(df)
    learning_outcomes = learning_outcomes.fillna("").astype(str)
    valid_lo_ids = set(learning_outcomes["LO_ID"].astype(str))
    lo_lookup = learning_outcomes.set_index("LO_ID").to_dict(orient="index")

    checks = []

    duplicate_ids = set(
        df.loc[df["Question_ID"].duplicated(keep=False), "Question_ID"]
        .replace("", pd.NA)
        .dropna()
    )

    for idx, row in df.iterrows():
        problems = []

        if not row["Question_ID"]:
            problems.append("Missing Question_ID")
        elif row["Question_ID"] in duplicate_ids:
            problems.append("Duplicate Question_ID")

        if not row["Level"]:
            problems.append("Missing Level")
        if not row["Topic_Code"]:
            problems.append("Missing Topic_Code")

        if not row["LO_ID"]:
            problems.append("Missing LO_ID")
        elif row["LO_ID"] not in valid_lo_ids:
            problems.append("LO_ID not found in Concept Master")
        else:
            official = lo_lookup[row["LO_ID"]]
            expected_level = clean_text(official.get("Level", ""))
            expected_topic = clean_text(official.get("Topic_Code", ""))
            if row["Level"] and expected_level and row["Level"] != expected_level:
                problems.append(f"Level does not match LO_ID (expected {expected_level})")
            if row["Topic_Code"] and expected_topic and row["Topic_Code"] != expected_topic:
                problems.append(f"Topic_Code does not match LO_ID (expected {expected_topic})")

        if not row["Question_Text"]:
            problems.append("Missing question text")

        option_values = []
        for option_col in ["Option_A", "Option_B", "Option_C", "Option_D"]:
            if not row[option_col]:
                problems.append(f"Missing {option_col}")
            option_values.append(row[option_col].casefold().strip())
        nonblank_options = [v for v in option_values if v]
        if len(nonblank_options) == 4 and len(set(nonblank_options)) != 4:
            problems.append("Options A-D must have distinct text")

        if row["Correct_Option"] not in VALID_OPTIONS:
            problems.append("Correct_Option must be A/B/C/D")

        if not row["Review_Status"]:
            problems.append("Missing Review_Status")
        elif row["Review_Status"] not in VALID_STATUSES:
            problems.append("Unknown Review_Status")

        if not row["Probe_Type"]:
            problems.append("Missing Probe_Type")
        elif row["Probe_Type"] not in VALID_PROBE_TYPES:
            problems.append("Unknown Probe_Type")

        if not row["Diagnostic_Use"]:
            problems.append("Missing Diagnostic_Use")
        elif row["Diagnostic_Use"] not in VALID_DIAGNOSTIC_USES:
            problems.append("Unknown Diagnostic_Use")

        checks.append({
            "Row": idx + 2,
            "Question_ID": row["Question_ID"],
            "LO_ID": row["LO_ID"],
            "Valid": not problems,
            "Problems": "; ".join(problems),
        })

    return pd.DataFrame(checks, columns=["Row", "Question_ID", "LO_ID", "Valid", "Problems"])


def assign_missing_question_ids(df, level=None, existing_bank=None):
    """Assign stable IDs to imported drafts that leave Question_ID blank.

    If `level` is omitted, each row's Level is used. This makes one template usable
    across P3-P6 and avoids asking Gemini Notebook to invent internal IDs.
    """
    df = normalize_question_bank(df)
    existing_bank = normalize_question_bank(
        existing_bank if existing_bank is not None
        else pd.DataFrame(columns=QUESTION_BANK_COLUMNS)
    )

    used = set(existing_bank["Question_ID"]) | set(df["Question_ID"])
    counters: dict[str, int] = {}

    def next_id(row_level: str) -> str:
        prefix_level = clean_text(level or row_level).upper() or "SCI"
        counters.setdefault(prefix_level, 1)
        while True:
            qid = f"{prefix_level}DQ{counters[prefix_level]:04d}"
            counters[prefix_level] += 1
            if qid not in used:
                used.add(qid)
                return qid

    today = date.today().isoformat()
    for idx in df.index[df["Question_ID"].eq("")]:
        df.at[idx, "Question_ID"] = next_id(df.at[idx, "Level"])
        df.at[idx, "Question_Version"] = df.at[idx, "Question_Version"] or "1"
        df.at[idx, "Created_Date"] = df.at[idx, "Created_Date"] or today

    return df



def update_question_record(df, question_id: str, updates: dict):
    """Return a copy of the bank with one question updated safely.

    Question_ID is the stable record key and cannot be changed here. Approval
    metadata is maintained locally so moderation does not depend on CSV edits.
    """
    df = normalize_question_bank(df)
    question_id = clean_text(question_id)
    if not question_id:
        raise ValueError("Question_ID is required.")

    matches = df.index[df["Question_ID"].eq(question_id)].tolist()
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one Question_ID {question_id!r}; found {len(matches)}.")

    idx = matches[0]
    allowed = set(QUESTION_BANK_COLUMNS) - {"Question_ID"}
    for field, value in updates.items():
        if field not in allowed:
            raise ValueError(f"Field cannot be edited here: {field}")
        df.at[idx, field] = clean_text(value)

    status = clean_text(df.at[idx, "Review_Status"])
    if status == "Approved":
        df.at[idx, "Approved_Date"] = clean_text(df.at[idx, "Approved_Date"]) or date.today().isoformat()
    else:
        df.at[idx, "Approved_Date"] = ""
        df.at[idx, "Approved_By"] = ""

    return normalize_question_bank(df)


def set_question_review_status(df, question_id: str, status: str):
    """Set Candidate/Approved/Rejected/Retired status for one question."""
    status = clean_text(status)
    if status not in VALID_STATUSES:
        raise ValueError(f"Unknown Review_Status: {status}")
    return update_question_record(df, question_id, {"Review_Status": status})


def set_questions_review_status(df, question_ids, status: str):
    """Set one review status for several stable Question_IDs in one operation."""
    status = clean_text(status)
    if status not in VALID_STATUSES:
        raise ValueError(f"Unknown Review_Status: {status}")

    out = normalize_question_bank(df)
    wanted = {clean_text(qid) for qid in question_ids if clean_text(qid)}
    if not wanted:
        return out

    known = set(out["Question_ID"].astype(str))
    missing = sorted(wanted - known)
    if missing:
        raise ValueError(f"Question_ID(s) not found: {', '.join(missing)}")

    today = date.today().isoformat()
    mask = out["Question_ID"].isin(wanted)
    out.loc[mask, "Review_Status"] = status
    if status == "Approved":
        blank_dates = mask & out["Approved_Date"].eq("")
        out.loc[blank_dates, "Approved_Date"] = today
    else:
        out.loc[mask, "Approved_Date"] = ""
        out.loc[mask, "Approved_By"] = ""
    return normalize_question_bank(out)


def prepare_multiple_imports(frames, existing_bank=None):
    """Prepare several imported CSV DataFrames as one stable candidate batch.

    Frames are processed sequentially so app-assigned Question_IDs stay unique
    across every uploaded file as well as the existing local bank.
    """
    existing = normalize_question_bank(
        existing_bank if existing_bank is not None
        else pd.DataFrame(columns=QUESTION_BANK_COLUMNS)
    )
    prepared_frames = []
    used_bank = existing.copy()

    for frame in frames:
        prepared = prepare_imported_question_bank(frame, existing_bank=used_bank)
        if prepared.empty:
            continue
        prepared_frames.append(prepared)
        used_bank = normalize_question_bank(pd.concat([used_bank, prepared], ignore_index=True))

    if not prepared_frames:
        return normalize_question_bank(pd.DataFrame(columns=QUESTION_BANK_COLUMNS))
    return normalize_question_bank(pd.concat(prepared_frames, ignore_index=True))


def merge_imported_questions(existing_bank, incoming, *, overwrite_existing=False):
    """Merge an imported batch with the local bank using Question_ID as the key.

    By default, matching stable IDs keep the existing local record. This protects
    teacher edits from being silently overwritten by a re-uploaded CSV.
    """
    existing = normalize_question_bank(existing_bank)
    incoming = normalize_question_bank(incoming)
    if existing.empty:
        return incoming
    if incoming.empty:
        return existing

    incoming_ids = set(incoming["Question_ID"].astype(str))
    if overwrite_existing:
        keep = existing[~existing["Question_ID"].astype(str).isin(incoming_ids)].copy()
        return normalize_question_bank(pd.concat([keep, incoming], ignore_index=True))

    existing_ids = set(existing["Question_ID"].astype(str))
    additions = incoming[~incoming["Question_ID"].astype(str).isin(existing_ids)].copy()
    return normalize_question_bank(pd.concat([existing, additions], ignore_index=True))


def make_question_bank_template_csv() -> bytes:
    """Blank import template containing exactly the columns the app accepts."""
    return pd.DataFrame(columns=QUESTION_BANK_COLUMNS).to_csv(index=False).encode("utf-8-sig")


def make_gemini_notebook_template_pack(learning_outcomes: pd.DataFrame, topics: pd.DataFrame) -> bytes:
    """Create a self-documenting ZIP for source-grounded question generation."""
    learning_outcomes = learning_outcomes.copy().fillna("")
    topics = topics.copy().fillna("")

    lo_columns = [
        c for c in [
            "LO_ID", "Topic_Code", "Level", "Theme", "Official Topic",
            "Official Domain", "Official Learning Outcome", "Official Details / Sub-points",
        ] if c in learning_outcomes.columns
    ]
    topic_columns = [
        c for c in ["Topic_Code", "Level", "Theme", "Official Topic"]
        if c in topics.columns
    ]

    valid_values = pd.DataFrame([
        {"Field": "Correct_Option", "Allowed values": "A | B | C | D", "Rule": "Required"},
        {"Field": "Probe_Type", "Allowed values": " | ".join(sorted(VALID_PROBE_TYPES)), "Rule": "Required"},
        {"Field": "Diagnostic_Use", "Allowed values": "Topic | Pre-WA | EOY | Any", "Rule": "Required; use Any if suitable for all"},
        {"Field": "Review_Status", "Allowed values": "Candidate | Approved | Rejected | Retired", "Rule": "AI-generated items should normally be Candidate"},
        {"Field": "LO_ID", "Allowed values": "Use only IDs in learning_outcome_reference.csv", "Rule": "Required; never invent an LO_ID"},
        {"Field": "Topic_Code", "Allowed values": "Must match the chosen LO_ID", "Rule": "Required"},
        {"Field": "Level", "Allowed values": "Must match the chosen LO_ID", "Rule": "Required"},
    ])

    prompt = """PRIMARY SCIENCE QUESTION BANK - GEMINI NOTEBOOK GENERATION INSTRUCTIONS

Use the official syllabus/TLG sources in this Gemini Notebook as the authority. Generate candidate text-only MCQs in question_bank_template.csv format.

Rules:
1. Do not invent curriculum content, LO_IDs, Topic_Codes or scope.
2. Map every question to exactly one LO_ID from learning_outcome_reference.csv.
3. Level and Topic_Code must match that LO_ID exactly.
4. Use only the controlled values in valid_values_reference.csv.
5. Set Review_Status to Candidate. A teacher will review and approve items later.
6. Leave Question_ID blank; the Science Diagnostic app will assign it.
7. Leave Question_Version blank or use 1.
8. Leave Times_Used as 0 and Last_Used blank.
9. Keep stems/options concise and age-appropriate. Test Science understanding rather than reading difficulty.
10. Use one clear best answer. Options A-D must all have different text.
11. Where appropriate, use official TLG alternative conceptions to design plausible distractors, and record the reference if available.
12. Do not add extra columns or rename existing columns.

Return/save the completed CSV with the same header order as question_bank_template.csv.
"""

    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("question_bank_template.csv", make_question_bank_template_csv())
        z.writestr("learning_outcome_reference.csv", learning_outcomes[lo_columns].to_csv(index=False).encode("utf-8-sig"))
        z.writestr("topic_reference.csv", topics[topic_columns].to_csv(index=False).encode("utf-8-sig"))
        z.writestr("valid_values_reference.csv", valid_values.to_csv(index=False).encode("utf-8-sig"))
        z.writestr("GEMINI_NOTEBOOK_INSTRUCTIONS.txt", prompt.encode("utf-8"))
    return mem.getvalue()


# Backward-compatible internal alias for V2.4 imports.
make_notebooklm_template_pack = make_gemini_notebook_template_pack


def delete_questions(df, question_ids):
    """Delete only explicitly supplied stable Question_IDs."""
    out = normalize_question_bank(df)
    wanted = {clean_text(qid) for qid in question_ids if clean_text(qid)}
    if not wanted:
        return out
    known = set(out["Question_ID"].astype(str))
    missing = sorted(wanted - known)
    if missing:
        raise ValueError(f"Question_ID(s) not found: {', '.join(missing)}")
    return normalize_question_bank(out[~out["Question_ID"].isin(wanted)].copy())


def delete_all_questions(df):
    """Return an empty Question Bank with the exact production schema."""
    normalize_question_bank(df)  # validate/normalise input shape before destructive operation
    return normalize_question_bank(pd.DataFrame(columns=QUESTION_BANK_COLUMNS))


def ensure_standard_bank_v1(
    master_path=None,
    template_path=None,
):
    """Ensure the audited 371-question Standard Bank v1 is usable after upgrade.

    The bundled CSV supplied by the user is the permanent default bank for every
    Sci Diagnostic release. It ships with all 371 questions already Approved.

    This helper repairs only known upgrade states:
    - missing/empty bank -> restore the bundled bank;
    - legacy all-Candidate bank -> make the bundled questions Approved;
    - an older pre-audit 371-question bundle -> upgrade those baseline question
      records to the audited wording while preserving usage counts, Teacher_Notes
      and any extra Admin-created questions.

    Once the audited baseline marker is present, ordinary later Admin moderation
    or edits are not overwritten on every app start.

    Returns ``(changed, message)``.
    """
    from .config import QUESTION_BANK_PATH, STANDARD_BANK_TEMPLATE_PATH

    master_path = master_path or QUESTION_BANK_PATH
    template_path = template_path or STANDARD_BANK_TEMPLATE_PATH

    template_path = pd.io.common.stringify_path(template_path)
    baseline = normalize_question_bank(pd.read_csv(template_path, dtype=str).fillna(""))
    if len(baseline) != 371 or baseline["Question_ID"].nunique() != 371:
        raise ValueError("Bundled Standard Bank v1 must contain exactly 371 unique questions.")
    if not baseline["Review_Status"].eq("Approved").all():
        raise ValueError("Bundled Standard Bank v1 must ship with all 371 questions Approved.")

    audit_marker = "Standard Bank v1: MOE age/scope audit 2026-09-05."
    if not baseline["Source_Note"].astype(str).str.contains(audit_marker, regex=False).all():
        raise ValueError("Bundled Standard Bank v1 is not the current MOE age/scope-audited default bank.")

    try:
        current = load_question_bank(master_path)
    except Exception:
        current = normalize_question_bank(pd.DataFrame(columns=QUESTION_BANK_COLUMNS))

    if current.empty:
        save_question_bank(baseline, master_path)
        return True, "Restored the bundled 371-question Approved audited Standard Bank v1."

    baseline_ids = set(baseline["Question_ID"].astype(str))
    current_ids = set(current["Question_ID"].astype(str))

    # Only perform a content migration when the full known baseline is present.
    # If an Admin intentionally removed baseline questions, do not silently add
    # them back during an ordinary app start.
    if baseline_ids.issubset(current_ids):
        baseline_rows = current["Question_ID"].astype(str).isin(baseline_ids)
        current_baseline = current.loc[baseline_rows].copy()
        legacy_statuses = set(current_baseline["Review_Status"].astype(str).str.strip())
        has_audit_marker = current_baseline["Source_Note"].astype(str).str.contains(
            audit_marker, regex=False
        )

        legacy_all_candidate = legacy_statuses.issubset({"", "Candidate"})
        legacy_pre_audit_bundle = not bool(has_audit_marker.any())

        if legacy_all_candidate or legacy_pre_audit_bundle:
            baseline_lookup = baseline.set_index("Question_ID")
            preserve_fields = {"Times_Used", "Last_Used", "Teacher_Notes"}

            for idx in current.index[baseline_rows]:
                qid = str(current.at[idx, "Question_ID"])
                old_status = clean_text(current.at[idx, "Review_Status"])
                preserved = {field: current.at[idx, field] for field in preserve_fields}

                # Replace the baseline-authored content with the user's audited
                # canonical row. Question_ID remains the stable join key.
                for field in QUESTION_BANK_COLUMNS:
                    if field == "Question_ID" or field in preserve_fields:
                        continue
                    current.at[idx, field] = baseline_lookup.at[qid, field]

                for field, value in preserved.items():
                    current.at[idx, field] = value

                # Respect an explicit Admin decision to reject/retire a question.
                # Legacy Candidate/Approved rows become the shipped Approved state.
                if old_status in {"Rejected", "Retired"}:
                    current.at[idx, "Review_Status"] = old_status
                    current.at[idx, "Approved_Date"] = ""
                    current.at[idx, "Approved_By"] = ""

            save_question_bank(current, master_path)
            if legacy_pre_audit_bundle:
                return True, "Upgraded the 371 Standard Bank v1 questions to the current MOE age/scope-audited default bank."
            return True, "Migrated the 371 Standard Bank v1 questions from Candidate to Approved."

    return False, "MOE age/scope-audited Standard Bank v1 is ready."

