from datetime import datetime
from io import BytesIO
import json
import random
import re
import zipfile

import pandas as pd


PRIMARY_LEVELS = ["P3", "P4", "P5", "P6"]


def cumulative_levels(assessment_level):
    """Return curriculum levels that may be included in an assessment.

    Primary Science assessment is cumulative: a teacher creating, for example,
    a P6 diagnostic may deliberately include approved questions from P3-P6.
    The UI still lets the teacher choose which of these levels to use.
    """
    if assessment_level not in PRIMARY_LEVELS:
        return [assessment_level]
    return PRIMARY_LEVELS[: PRIMARY_LEVELS.index(assessment_level) + 1]


def eligible_questions(bank, level=None, topic_codes=None, diagnostic_use=None, levels=None):
    approved = bank[bank["Review_Status"].eq("Approved")].copy()

    allowed_levels = list(levels or ([] if level is None else [level]))
    if allowed_levels:
        approved = approved[approved["Level"].isin(allowed_levels)]

    if topic_codes:
        approved = approved[approved["Topic_Code"].isin(topic_codes)]

    if diagnostic_use:
        approved = approved[
            approved["Diagnostic_Use"].isin([diagnostic_use, "Any", ""])
        ]

    return approved.reset_index(drop=True)


def scope_filter_audit(bank, level, topic_codes=None, diagnostic_use=None, levels=None):
    """Explain how many questions survive each Create Diagnostic filter."""
    approved = bank[bank["Review_Status"].eq("Approved")].copy()
    allowed_levels = list(levels or [level])
    at_level = approved[approved["Level"].isin(allowed_levels)].copy()
    at_topics = at_level.copy()
    if topic_codes:
        at_topics = at_topics[at_topics["Topic_Code"].isin(topic_codes)]

    eligible = at_topics.copy()
    if diagnostic_use:
        eligible = eligible[eligible["Diagnostic_Use"].isin([diagnostic_use, "Any", ""])]

    available_uses = sorted(
        u for u in at_topics["Diagnostic_Use"].dropna().astype(str).unique()
        if u
    )
    available_topics = sorted(
        t for t in at_level["Topic_Code"].dropna().astype(str).unique()
        if t
    )

    return {
        "approved_total": int(len(approved)),
        "approved_at_level": int(len(at_level)),
        "approved_at_topics": int(len(at_topics)),
        "eligible": int(len(eligible)),
        "available_diagnostic_uses": available_uses,
        "available_topics": available_topics,
    }


def _ordered_lo_candidates(group, rng):
    """Order one LO's candidates to favour variety and less-used questions."""
    group = group.copy()
    if "Times_Used" in group.columns:
        group["Times_Used_num"] = pd.to_numeric(group["Times_Used"], errors="coerce").fillna(0)
    else:
        group["Times_Used_num"] = 0
    if "Probe_Type" in group.columns:
        group["Probe_Type"] = group["Probe_Type"].fillna("").astype(str)
    else:
        group["Probe_Type"] = ""
    group["_tie"] = [rng.random() for _ in range(len(group))]

    # First choose the least-used candidate from each distinct probe type,
    # preserving least-used order, then append the remainder. This gives probe
    # variety without allowing a heavily reused question to jump the queue.
    ordered = []
    remaining = group.sort_values(["Times_Used_num", "_tie", "Question_ID"]).copy()
    seen_idx = set()
    seen_probe = set()
    for idx, row in remaining.iterrows():
        probe = row["Probe_Type"]
        if probe not in seen_probe:
            ordered.append(idx)
            seen_idx.add(idx)
            seen_probe.add(probe)
    for idx in remaining.index:
        if idx not in seen_idx:
            ordered.append(idx)
    return ordered


def select_balanced_questions(pool, target_count, seed=2026):
    """Auto-build a balanced diagnostic from an approved question pool.

    Selection is deterministic for a given seed. It round-robins across LO_IDs,
    favours less-used questions, and seeks probe-type variety within each LO.
    """
    if pool.empty or target_count <= 0:
        return pool.iloc[0:0].copy()

    target_count = min(int(target_count), len(pool))
    rng = random.Random(seed)
    work = pool.copy().reset_index(drop=True)

    groups = {}
    for lo_id, group in work.groupby("LO_ID", sort=True, dropna=False):
        groups[str(lo_id)] = _ordered_lo_candidates(group, rng)

    selected_idx = []
    active = list(groups.keys())
    while active and len(selected_idx) < target_count:
        next_active = []
        for lo_id in active:
            if groups[lo_id] and len(selected_idx) < target_count:
                selected_idx.append(groups[lo_id].pop(0))
            if groups[lo_id]:
                next_active.append(lo_id)
        active = next_active

    return work.loc[selected_idx].reset_index(drop=True)


def select_comprehensive_questions(pool, seed=2026, minimum_per_lo=2):
    """Build a no-fixed-cap comprehensive set without selecting everything blindly.

    The set aims for at least two independent probes per represented LO where
    available, then adds questions needed to represent every non-empty TLG Key
    Idea and Alternative Conception tag in the selected pool. This uses only the
    metadata already present in the Question Bank.
    """
    if pool.empty:
        return pool.iloc[0:0].copy()

    work = pool.copy().reset_index(drop=True)
    lo_sizes = work.groupby("LO_ID", dropna=False).size()
    base_target = int(sum(min(int(minimum_per_lo), int(n)) for n in lo_sizes))
    selected = select_balanced_questions(work, base_target, seed=seed)
    selected_ids = set(selected["Question_ID"].astype(str))

    def add_best_for_tag(column, value):
        nonlocal selected_ids
        candidates = work[work[column].fillna("").astype(str).eq(value)].copy()
        if candidates.empty or any(candidates["Question_ID"].astype(str).isin(selected_ids)):
            return
        if "Times_Used" in candidates.columns:
            candidates["Times_Used_num"] = pd.to_numeric(candidates["Times_Used"], errors="coerce").fillna(0)
        else:
            candidates["Times_Used_num"] = 0
        best = candidates.sort_values(["Times_Used_num", "Question_ID"]).iloc[0]
        selected_ids.add(str(best["Question_ID"]))

    for column in ["TLG_Key_Idea_Ref", "Alternative_Conception_Ref"]:
        if column not in work.columns:
            continue
        values = sorted({
            x.strip() for x in work[column].fillna("").astype(str)
            if x.strip()
        })
        for value in values:
            add_best_for_tag(column, value)

    chosen = work[work["Question_ID"].astype(str).isin(selected_ids)].copy()
    # Re-run the balancing engine over exactly the chosen set so the final order
    # is spread across LOs rather than grouped by source dataframe order.
    return select_balanced_questions(chosen, len(chosen), seed=seed)


def comprehensive_coverage_audit(
    selected,
    learning_outcomes,
    level=None,
    topic_codes=None,
    levels=None,
):
    """Summarise what a comprehensive diagnostic can genuinely verify.

    Learning Outcomes are checked against the official Concept Master for all
    selected topic codes, including lower-level topics in cumulative diagnostics.
    TLG Key Ideas and Alternative Conceptions are counted from explicit Question
    Bank tags. The Concept Master has no separate Success Criteria field, so
    official Details/Sub-points are surfaced for teacher review rather than being
    claimed as independently covered.
    """
    selected = selected.copy().fillna("")
    learning_outcomes = learning_outcomes.copy().fillna("")
    topic_codes = list(topic_codes or [])

    official = learning_outcomes.copy()
    if levels:
        official = official[official["Level"].isin(list(levels))]
    elif level:
        official = official[official["Level"].eq(level)]
    if topic_codes:
        official = official[official["Topic_Code"].isin(topic_codes)]

    required_lo_ids = [x for x in official["LO_ID"].astype(str).tolist() if x]
    covered_lo_ids = set(selected.get("LO_ID", pd.Series(dtype=str)).astype(str))
    missing_lo_ids = [lo for lo in required_lo_ids if lo not in covered_lo_ids]

    key_ideas = set(
        x.strip() for x in selected.get("TLG_Key_Idea_Ref", pd.Series(dtype=str)).astype(str) if x.strip()
    )
    alternatives = set(
        x.strip() for x in selected.get("Alternative_Conception_Ref", pd.Series(dtype=str)).astype(str) if x.strip()
    )

    cols = [c for c in [
        "Level", "Topic_Code", "LO_ID", "Official Domain", "Official Learning Outcome",
        "Official Details / Sub-points"
    ] if c in official.columns]
    coverage = official[cols].copy()
    if not coverage.empty:
        coverage["Approved question count"] = coverage["LO_ID"].map(
            selected.groupby("LO_ID").size().to_dict()
        ).fillna(0).astype(int)
        coverage["LO covered"] = coverage["Approved question count"].gt(0)

    return {
        "required_lo_count": len(required_lo_ids),
        "covered_lo_count": len(set(required_lo_ids) & covered_lo_ids),
        "missing_lo_ids": missing_lo_ids,
        "key_idea_count": len(key_ideas),
        "alternative_conception_count": len(alternatives),
        "official_coverage": coverage.reset_index(drop=True),
    }


def coverage_table(selected):
    if selected.empty:
        return pd.DataFrame(columns=["Level", "Topic_Code", "LO_ID", "Questions"])

    group_cols = [c for c in ["Level", "Topic_Code", "LO_ID"] if c in selected.columns]
    return (
        selected.groupby(group_cols)
        .size()
        .reset_index(name="Questions")
        .sort_values(group_cols)
        .reset_index(drop=True)
    )


def create_diagnostic_id(level, diagnostic_use):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_use = re.sub(r"[^A-Za-z0-9]+", "", diagnostic_use)
    return f"{level}_{safe_use}_{timestamp}"


def build_diagnostic_package(selected, title, diagnostic_id=None):
    selected = selected.copy().reset_index(drop=True)
    if diagnostic_id is None:
        level = selected["Level"].iloc[0] if not selected.empty else "SCI"
        diagnostic_use = (
            selected["Diagnostic_Use"].iloc[0]
            if not selected.empty else "Diagnostic"
        )
        diagnostic_id = create_diagnostic_id(level, diagnostic_use)

    selected.insert(0, "Question_Number", range(1, len(selected) + 1))
    selected.insert(0, "Diagnostic_ID", diagnostic_id)

    student = selected[
        [
            "Diagnostic_ID","Question_Number","Question_ID",
            "Question_Text","Option_A","Option_B","Option_C","Option_D"
        ]
    ].copy()

    answer_key = selected[
        [
            "Diagnostic_ID","Question_Number","Question_ID","LO_ID",
            "Correct_Option","Answer_Explanation","Probe_Type",
            "Alternative_Conception_Ref","Source_Note"
        ]
    ].copy()

    blueprint = selected[
        [
            "Diagnostic_ID","Question_Number","Question_ID","Level",
            "Topic_Code","LO_ID","Probe_Type","Diagnostic_Use",
            "TLG_Key_Idea_Ref","Alternative_Conception_Ref"
        ]
    ].copy()

    forms = selected[
        [
            "Diagnostic_ID","Question_Number","Question_ID","Question_Text",
            "Option_A","Option_B","Option_C","Option_D","Correct_Option"
        ]
    ].copy()
    forms.insert(1, "Form_Title", title)

    metadata = {
        "diagnostic_id": diagnostic_id,
        "title": title,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "question_count": len(selected),
        "question_ids": selected["Question_ID"].tolist(),
    }

    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("student_questions.csv", student.to_csv(index=False))
        z.writestr("answer_key.csv", answer_key.to_csv(index=False))
        z.writestr("diagnostic_blueprint.csv", blueprint.to_csv(index=False))
        z.writestr("google_forms_ready.csv", forms.to_csv(index=False))
        z.writestr("diagnostic_manifest.json", json.dumps(metadata, indent=2))

    return mem.getvalue(), metadata
