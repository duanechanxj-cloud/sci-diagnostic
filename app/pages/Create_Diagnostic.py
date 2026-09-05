from pathlib import Path
import hashlib
import io
import json
import sys
import zipfile

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.classes import load_classes, active_classes_for_level, class_display_name, class_key_from_row
from src.config import CLASSES_PATH, GOOGLE_TOKEN_PATH, GOOGLE_FORMS_DIR
from src.curriculum import load_concept_master
from src.diagnostic import (
    build_diagnostic_package,
    comprehensive_coverage_audit,
    coverage_table,
    create_diagnostic_id,
    cumulative_levels,
    eligible_questions,
    select_balanced_questions,
    select_comprehensive_questions,
)
from src.google_forms_api import (
    create_google_diagnostic_form,
    list_form_manifests,
    make_qr_png,
    save_form_manifest,
)
from src.question_bank import load_question_bank
from src.persistence import ensure_project_drive_layout
from src.ui import page_header, metric_card
from src.runtime import get_google_credentials_runtime, persist_runtime_state

page_header(
    "Create Diagnostic",
    "Choose the assessment level, include topics from that level or earlier levels, then let Auto Build suggest a balanced set or select questions manually.",
)

bank = load_question_bank()
approved = bank[bank["Review_Status"].eq("Approved")].copy()
if approved.empty:
    st.warning("There are no Approved questions in the Question Bank yet. Review and approve questions before creating a diagnostic.")
    st.stop()

learning_outcomes, _, topics_reference = load_concept_master()

st.markdown(
    '<div class="step-line">1 &nbsp; Scope &nbsp;&nbsp; → &nbsp;&nbsp; 2 &nbsp; Questions &nbsp;&nbsp; → &nbsp;&nbsp; 3 &nbsp; Classes &nbsp;&nbsp; → &nbsp;&nbsp; 4 &nbsp; QR codes</div>',
    unsafe_allow_html=True,
)

assessment_level = st.selectbox(
    "Assessment level",
    ["P3", "P4", "P5", "P6"],
    help="This is the class level taking the diagnostic. Lower-level Science topics can still be included because assessment is cumulative.",
)

allowed_source_levels = cumulative_levels(assessment_level)
approved_source_levels = [
    lvl for lvl in allowed_source_levels
    if approved["Level"].eq(lvl).any()
]
if not approved_source_levels:
    st.warning(f"There are no Approved questions available for {assessment_level} or its earlier levels.")
    st.stop()

source_levels = st.multiselect(
    "Question levels to include",
    options=approved_source_levels,
    default=[assessment_level] if assessment_level in approved_source_levels else approved_source_levels,
    help=(
        "Choose the curriculum levels whose topics may appear in this diagnostic. "
        "For example, a P4 assessment can include P3 and P4 topics; a P6 assessment can include P3, P4, P5 and P6 topics."
    ),
)
if not source_levels:
    st.info("Select at least one question level to continue.")
    st.stop()

level_pool = approved[approved["Level"].isin(source_levels)].copy()
available_topic_codes = sorted(t for t in level_pool["Topic_Code"].dropna().unique() if t)
topic_name_lookup = (
    topics_reference.set_index("Topic_Code")["Official Topic"].to_dict()
    if not topics_reference.empty else {}
)
topic_level_lookup = (
    topics_reference.set_index("Topic_Code")["Level"].to_dict()
    if not topics_reference.empty else {}
)

selected_topics = st.multiselect(
    "Topics",
    available_topic_codes,
    default=available_topic_codes[:1],
    format_func=lambda code: f"{topic_level_lookup.get(code, '')} · {topic_name_lookup.get(code, code)}",
    help="Mix any available topics from the question levels you selected above.",
)
if not selected_topics:
    st.info("Select at least one topic to continue.")
    st.stop()

# Diagnostic_Use remains useful metadata in the Question Bank, but it does not
# restrict what a teacher may combine when constructing a diagnostic.
pool = eligible_questions(
    bank,
    levels=source_levels,
    topic_codes=selected_topics,
    diagnostic_use=None,
)
if pool.empty:
    st.warning("No Approved questions are available for the selected topics.")
    st.stop()

build_method = st.radio(
    "Question selection",
    ["Auto Build", "Manual selection"],
    horizontal=True,
    help="Auto Build balances the set across Learning Outcomes and favours a mix of probe types. You can still use Manual selection whenever you want full control.",
)

comprehensive = st.checkbox(
    "Comprehensive testing",
    value=False,
    disabled=(build_method == "Manual selection"),
    help=(
        "Auto Build has no fixed question-count limit in this mode. It aims for repeated evidence across each available Learning Outcome and includes tagged TLG Key Ideas and Alternative Conceptions where the Approved bank supports them."
    ),
)

st.divider()
st.subheader("Choose questions")

if build_method == "Auto Build":
    if comprehensive:
        selected = select_comprehensive_questions(pool, seed=2026, minimum_per_lo=2)
        st.info(
            f"Comprehensive Auto Build selected {len(selected)} questions from {len(pool)} Approved questions in scope. "
            "There is no fixed question-count cap."
        )
    else:
        default_count = min(max(1, len(pool)), 12)
        target_count = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=int(len(pool)),
            value=int(default_count),
            step=1,
            help="Auto Build spreads the requested number across the available Learning Outcomes and favours less-used questions and varied probe types.",
        )
        selected = select_balanced_questions(pool, int(target_count), seed=2026)
        st.success(
            f"Auto Build suggested {len(selected)} questions across {selected['LO_ID'].nunique()} Learning Outcomes and {selected['Topic_Code'].nunique()} topics."
        )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Selected", len(selected), f"{len(pool)} Approved in scope")
    with m2:
        metric_card("Learning outcomes", selected["LO_ID"].nunique(), "Distinct LO_IDs represented")
    with m3:
        metric_card("Topics", selected["Topic_Code"].nunique(), "Topics represented")
    with m4:
        metric_card("Question levels", selected["Level"].nunique(), "Curriculum levels represented")

    with st.expander("Review Auto Build selection", expanded=True):
        st.dataframe(
            selected[["Level", "Question_ID", "Topic_Code", "LO_ID", "Question_Text", "Probe_Type", "TLG_Key_Idea_Ref"]],
            use_container_width=True,
            hide_index=True,
        )

else:
    st.caption(
        "Tick the questions you want. You can mix questions from any selected lower or current curriculum level and any selected topic."
    )

    selection_key = hashlib.sha256(
        json.dumps({
            "assessment_level": assessment_level,
            "source_levels": sorted(source_levels),
            "topics": sorted(selected_topics),
        }, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    state_key = f"v244_manual_ids_{selection_key}"
    previous_ids = set(st.session_state.get(state_key, []))

    chooser = pool[[
        "Question_ID", "Level", "Topic_Code", "LO_ID", "Question_Text", "Probe_Type",
        "TLG_Key_Idea_Ref", "Alternative_Conception_Ref"
    ]].copy()
    chooser.insert(0, "Include", chooser["Question_ID"].isin(previous_ids))
    chooser = chooser.sort_values(["Level", "Topic_Code", "LO_ID", "Question_ID"]).reset_index(drop=True)

    edited_chooser = st.data_editor(
        chooser,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        height=min(620, 115 + max(1, len(chooser)) * 36),
        column_config={
            "Include": st.column_config.CheckboxColumn("Include", width="small"),
            "Level": st.column_config.TextColumn("Level", width="small"),
            "Question_Text": st.column_config.TextColumn("Question", width="large"),
            "Question_ID": st.column_config.TextColumn("Question ID", width="small"),
            "Topic_Code": st.column_config.TextColumn("Topic", width="small"),
            "LO_ID": st.column_config.TextColumn("Learning outcome", width="medium"),
            "Probe_Type": st.column_config.TextColumn("Probe", width="medium"),
        },
        disabled=[
            "Question_ID", "Level", "Topic_Code", "LO_ID", "Question_Text", "Probe_Type",
            "TLG_Key_Idea_Ref", "Alternative_Conception_Ref",
        ],
        key=f"v244_question_picker_{selection_key}",
    )
    selected_ids = edited_chooser.loc[edited_chooser["Include"], "Question_ID"].astype(str).tolist()
    st.session_state[state_key] = selected_ids
    selected = pool[pool["Question_ID"].astype(str).isin(selected_ids)].copy()
    order_lookup = {qid: i for i, qid in enumerate(selected_ids)}
    selected["_order"] = selected["Question_ID"].map(order_lookup)
    selected = selected.sort_values("_order").drop(columns="_order").reset_index(drop=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Selected", len(selected), f"{len(pool)} Approved questions available")
    with m2:
        metric_card("Learning outcomes", selected["LO_ID"].nunique() if not selected.empty else 0, "Distinct LO_IDs selected")
    with m3:
        metric_card("Topics", selected["Topic_Code"].nunique() if not selected.empty else 0, "Topics represented")
    with m4:
        metric_card("Question levels", selected["Level"].nunique() if not selected.empty else 0, "Curriculum levels represented")

    if selected.empty:
        st.info("Tick at least one question to continue.")
        st.stop()

# Every build method gets the same official Learning Outcome coverage check.
# This is deliberately a warning, not a hard block: a teacher may intentionally
# create a short diagnostic that samples only part of a topic.
selection_audit = comprehensive_coverage_audit(
    selected,
    learning_outcomes=learning_outcomes,
    levels=source_levels,
    topic_codes=selected_topics,
)

st.markdown("#### Learning Outcome coverage")
coverage_left, coverage_right = st.columns([1, 3])
with coverage_left:
    metric_card(
        "Official LOs",
        f"{selection_audit['covered_lo_count']}/{selection_audit['required_lo_count']}",
        "Covered by at least one selected question",
    )
with coverage_right:
    if selection_audit["missing_lo_ids"]:
        st.warning(
            f"This diagnostic does not cover {len(selection_audit['missing_lo_ids'])} official Learning Outcome"
            f"{'s' if len(selection_audit['missing_lo_ids']) != 1 else ''} in the selected topic scope. "
            "You may continue if this is intentional, or add questions before building the diagnostic."
        )
        missing_table = selection_audit["official_coverage"]
        if not missing_table.empty and "LO covered" in missing_table.columns:
            missing_table = missing_table.loc[~missing_table["LO covered"]].copy()
            display_columns = [
                column for column in [
                    "Level", "Topic_Code", "LO_ID", "Official Learning Outcome"
                ] if column in missing_table.columns
            ]
            if display_columns:
                st.dataframe(
                    missing_table[display_columns],
                    use_container_width=True,
                    hide_index=True,
                )
    else:
        st.success("All official Learning Outcomes in the selected topic scope are covered by the current question set.")

if comprehensive:
    t1, t2 = st.columns(2)
    with t1:
        metric_card("TLG Key Ideas", selection_audit["key_idea_count"], "Distinct tagged Key Ideas")
    with t2:
        metric_card("Misconceptions", selection_audit["alternative_conception_count"], "Distinct tagged Alternative Conceptions")
    with st.expander("Review comprehensive coverage", expanded=False):
        if not selection_audit["official_coverage"].empty:
            st.dataframe(selection_audit["official_coverage"], use_container_width=True, hide_index=True)

st.divider()
title = st.text_input("Diagnostic title", f"{assessment_level} Science Diagnostic")
if not title.strip():
    st.warning("Give the diagnostic a title before building it.")
    st.stop()

if build_method == "Auto Build" and comprehensive:
    selection_mode = "Comprehensive Auto Build"
elif build_method == "Auto Build":
    selection_mode = "Auto Build"
else:
    selection_mode = "Custom"

fingerprint_payload = {
    "assessment_level": assessment_level,
    "source_levels": sorted(source_levels),
    "topics": sorted(selected_topics),
    "mode": selection_mode,
    "question_ids": selected["Question_ID"].astype(str).tolist(),
    "title": title.strip(),
}
current_fingerprint = hashlib.sha256(
    json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")
).hexdigest()

if st.button("Build diagnostic", type="primary", use_container_width=True):
    diagnostic_id = create_diagnostic_id(assessment_level, selection_mode)
    package, metadata = build_diagnostic_package(selected, title.strip(), diagnostic_id=diagnostic_id)
    metadata.update({
        "level": assessment_level,
        "assessment_level": assessment_level,
        "question_levels": list(source_levels),
        "selection_mode": selection_mode,
        "topic_codes": list(selected_topics),
        "title": title.strip(),
        "selection_fingerprint": current_fingerprint,
        # Kept only for backward compatibility with existing form manifests.
        "diagnostic_type": selection_mode,
    })
    st.session_state["v24_selected_diagnostic"] = selected
    st.session_state["v24_diagnostic_package"] = package
    st.session_state["v24_diagnostic_metadata"] = metadata

built_selected = st.session_state.get("v24_selected_diagnostic")
metadata = st.session_state.get("v24_diagnostic_metadata")

if metadata and metadata.get("selection_fingerprint") != current_fingerprint:
    st.info("The scope, question selection or title changed. Click Build diagnostic again to use the updated set.")
    st.stop()

if built_selected is None or built_selected.empty or not metadata:
    st.stop()

selected = built_selected

st.divider()
st.subheader("Question set")
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Questions", len(selected), metadata.get("selection_mode", "Custom"))
with c2:
    metric_card("Learning outcomes", selected["LO_ID"].nunique(), "Distinct LO_IDs represented")
with c3:
    metric_card("Topics", selected["Topic_Code"].nunique(), "Distinct topic codes represented")
with c4:
    metric_card("Question levels", selected["Level"].nunique(), "Curriculum levels represented")

with st.expander("Review coverage and selected questions", expanded=False):
    st.dataframe(coverage_table(selected), use_container_width=True, hide_index=True)
    st.dataframe(
        selected[["Level", "Question_ID", "Topic_Code", "LO_ID", "Question_Text", "Correct_Option"]],
        use_container_width=True,
        hide_index=True,
    )

st.download_button(
    "Download diagnostic backup",
    st.session_state["v24_diagnostic_package"],
    file_name=f"{metadata['diagnostic_id']}.zip",
    mime="application/zip",
    use_container_width=True,
)

active_level = metadata["level"]
active_mode = metadata.get("selection_mode", "Custom")
active_topics = metadata["topic_codes"]
active_title = metadata["title"]

classes = load_classes(CLASSES_PATH)
eligible_classes = active_classes_for_level(classes, active_level)
if eligible_classes.empty:
    st.info(
        f"No active {active_level} classes are configured. "
        "Ask an Admin to update the class master before generating class Forms."
    )
    st.stop()

st.divider()
st.subheader("Choose classes")
class_rows = {
    class_key_from_row(row): row
    for _, row in eligible_classes.iterrows()
}
class_options = {
    key: class_display_name(row)
    for key, row in class_rows.items()
}
selected_codes = st.multiselect(
    "Classes taking this diagnostic",
    options=list(class_options.keys()),
    format_func=lambda key: class_options[key],
    default=[],
    help="Select only the class or classes that will take this diagnostic.",
)
if not selected_codes:
    st.info("Select at least one class to continue.")
    st.stop()

all_manifests = list_form_manifests(GOOGLE_FORMS_DIR)
existing = {
    m.get("class_code"): m
    for m in all_manifests
    if m.get("diagnostic_id") == metadata["diagnostic_id"]
}

st.markdown("**Number of pupils taking this diagnostic**")
st.caption(
    "This is not saved as permanent class enrolment. It is used only to create the class index-number dropdown for this diagnostic Form."
)
student_counts = {}
for code in selected_codes:
    manifest = existing.get(code)
    default_count = int(manifest.get("student_count", manifest.get("index_max", 40))) if manifest else 40
    student_counts[code] = int(
        st.number_input(
            class_options[code],
            min_value=1,
            max_value=60,
            value=max(1, min(60, default_count)),
            step=1,
            key=f"student_count_{metadata['diagnostic_id']}_{code}",
            disabled=bool(manifest),
            help=(
                "This Form already exists, so its pupil count is fixed."
                if manifest
                else "Enter the number of pupils in this class who will take the diagnostic."
            ),
        )
    )


creds = None
try:
    creds = get_google_credentials_runtime()
except Exception as exc:
    st.warning(f"Google connection needs attention: {exc}")

missing_codes = [code for code in selected_codes if code not in existing]
if not creds:
    st.info("Connect your Google account on Google Connection before creating the class Forms.")
elif missing_codes:
    if st.button(
        f"Create {len(missing_codes)} class Form{'s' if len(missing_codes) != 1 else ''}",
        type="primary",
        use_container_width=True,
    ):
        progress = st.progress(0)
        status = st.empty()
        created_count = 0
        drive_layout = ensure_project_drive_layout(creds)
        for i, code in enumerate(missing_codes, start=1):
            row = class_rows[code]
            class_name = class_display_name(row)
            status.write(f"Creating {class_name}…")
            try:
                manifest = create_google_diagnostic_form(
                    selected,
                    title=f"{active_title} — {class_name}",
                    credentials=creds,
                    description=(
                        f"{class_name}. Select your own class index number carefully, then answer every Science question. "
                        "This is a learning diagnostic used to identify concepts for revision."
                    ),
                    identity_prompt="Class index number",
                    identity_help=f"Select your own class index number carefully (1-{student_counts[code]}).",
                    class_code=code,
                    class_name=class_name,
                    level=active_level,
                    index_min=1,
                    index_max=student_counts[code],
                    diagnostic_id=metadata["diagnostic_id"],
                    diagnostic_type=active_mode,
                    drive_folder_id=drive_layout["forms_id"],
                )
                manifest["student_count"] = student_counts[code]
                manifest["topic_codes"] = active_topics
                manifest["question_levels"] = metadata.get("question_levels", [active_level])
                manifest["selection_mode"] = active_mode
                save_form_manifest(manifest, GOOGLE_FORMS_DIR)
                existing[code] = manifest
                created_count += 1
            except Exception as exc:
                st.error(f"{class_name}: {type(exc).__name__}: {exc}")
            progress.progress(i / len(missing_codes))
        status.empty()
        if created_count:
            persist_runtime_state()
            st.success(f"Created {created_count} class Form{'s' if created_count != 1 else ''}.")
else:
    st.success("All selected classes already have a Form for this diagnostic.")

ready = [existing[c] for c in selected_codes if c in existing]
if ready:
    st.divider()
    st.subheader("Class QR codes")
    st.caption("Each QR belongs to exactly one class. Pupils select their class index number from a dropdown.")

    for start in range(0, len(ready), 3):
        cols = st.columns(3)
        for col, manifest in zip(cols, ready[start:start + 3]):
            with col:
                st.markdown(f"### {manifest['class_name']}")
                qr = make_qr_png(manifest["responder_uri"])
                st.image(qr, width=230)
                st.link_button("Open pupil Form", manifest["responder_uri"], use_container_width=True)
                st.download_button(
                    "Download QR",
                    qr.getvalue(),
                    file_name=(
                        f"{metadata['diagnostic_id']}_{manifest['class_name'].replace(' ', '_')}_QR.png"
                    ),
                    mime="image/png",
                    key=f"qr_{manifest['form_id']}",
                    use_container_width=True,
                )
                st.caption(
                    f"{manifest.get('student_count', manifest['index_max'])} pupils · "
                    f"{manifest['question_count']} questions"
                )

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        launch_rows = []
        for manifest in ready:
            qr = make_qr_png(manifest["responder_uri"])
            z.writestr(
                f"{manifest['class_name'].replace(' ', '_')}_QR.png",
                qr.getvalue(),
            )
            launch_rows.append({
                "Level": manifest.get("level", active_level),
                "Class_Name": manifest["class_name"],
                "Form_ID": manifest["form_id"],
                "Responder_URL": manifest["responder_uri"],
                "Edit_URL": manifest["edit_uri"],
            })
        z.writestr("class_form_links.csv", pd.DataFrame(launch_rows).to_csv(index=False))
    st.download_button(
        "Download all class QR codes",
        mem.getvalue(),
        file_name=f"{metadata['diagnostic_id']}_Class_QRs.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )
