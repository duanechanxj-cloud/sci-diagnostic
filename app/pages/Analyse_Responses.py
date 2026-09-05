from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis import add_curriculum_wording, rank_class_revision_priorities
from src.config import GOOGLE_TOKEN_PATH, GOOGLE_FORMS_DIR, RESPONSES_DIR
from src.curriculum import load_concept_master
from src.exports import dataframe_to_excel_bytes
from src.forms import audit_index_numbers, api_responses_wide_to_long, option_text_to_letter, reaudit_responses_by_manifest
from src.google_forms_api import list_form_manifests, fetch_google_form_responses
from src.privacy import anonymise_student_data
from src.question_bank import load_question_bank
from src.scoring import score_responses, add_curriculum_to_scored, student_lo_summary, student_topic_summary, class_lo_summary
from src.ui import page_header, metric_card
from src.runtime import get_google_credentials_runtime, persist_runtime_state

page_header(
    "Analyse Responses",
    "Fetch every class Form in a diagnostic, check index numbers and duplicate submissions, then score everything locally.",
)

bank = load_question_bank()
if bank.empty:
    st.warning("The Question Bank is empty.")
    st.stop()

manifests = [m for m in list_form_manifests(GOOGLE_FORMS_DIR) if m.get("diagnostic_id") and m.get("class_code")]
if not manifests:
    st.info("No V2.4.1 class Forms have been created yet.")
    st.stop()

campaigns = {}
for m in manifests:
    campaigns.setdefault(m["diagnostic_id"], []).append(m)
labels = {}
for diagnostic_id, items in campaigns.items():
    first = items[0]
    base_title = first.get("title", diagnostic_id).rsplit(" — ", 1)[0]
    labels[diagnostic_id] = f"{base_title} · {len(items)} class{'es' if len(items) != 1 else ''}"

selected_id = st.selectbox("Diagnostic", list(campaigns.keys()), format_func=lambda x: labels[x])
selected_manifests = sorted(campaigns[selected_id], key=lambda m: m.get("class_name", ""))
class_codes = [m["class_code"] for m in selected_manifests]
selected_codes = st.multiselect(
    "Classes to fetch",
    class_codes,
    default=class_codes,
    format_func=lambda code: next(m["class_name"] for m in selected_manifests if m["class_code"] == code),
)
active_manifests = [m for m in selected_manifests if m["class_code"] in selected_codes]

if st.button("Fetch responses", type="primary", disabled=not active_manifests, use_container_width=True):
    try:
        creds = get_google_credentials_runtime()
        if not creds:
            st.error("Google is not connected.")
        else:
            audited_frames = []
            progress = st.progress(0)
            for i, manifest in enumerate(active_manifests, start=1):
                fetched = fetch_google_form_responses(manifest, creds)
                RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
                fetched.to_csv(RESPONSES_DIR / f"{manifest['form_id']}_responses.csv", index=False, encoding="utf-8-sig")
                audited = audit_index_numbers(fetched, manifest["index_min"], manifest["index_max"])
                audited["Form_ID"] = manifest["form_id"]
                audited_frames.append(audited)
                progress.progress(i / len(active_manifests))
            combined = pd.concat(audited_frames, ignore_index=True) if audited_frames else pd.DataFrame()
            st.session_state["v24_raw_responses"] = combined
            st.session_state["v24_active_manifests"] = active_manifests
            st.session_state["v24_fetched_diagnostic_id"] = selected_id
            persist_runtime_state()
            for key in ["scored_enriched", "student_lo_summary", "student_topic_summary", "class_summary", "active_diagnostic_id"]:
                st.session_state.pop(key, None)
    except Exception as exc:
        st.error(f"Could not fetch responses: {type(exc).__name__}: {exc}")

wide = st.session_state.get("v24_raw_responses")
active_session_manifests = st.session_state.get("v24_active_manifests", [])
if wide is None or st.session_state.get("v24_fetched_diagnostic_id") != selected_id:
    st.stop()

st.divider()
st.subheader("Submission check")
review_count = int(wide["Needs_Review"].sum()) if not wide.empty else 0
c1, c2, c3 = st.columns(3)
with c1: metric_card("Submissions", len(wide))
with c2: metric_card("Classes", wide["Class_Code"].nunique() if not wide.empty else 0)
with c3: metric_card("Needs review", review_count, "Duplicates or invalid index numbers")

review_cols = ["Response_ID", "Class_Name", "Index_Number_Raw", "Timestamp", "Duplicate_Submission_Count", "Needs_Review"]
st.dataframe(wide[review_cols], use_container_width=True, hide_index=True)
if review_count:
    st.warning("Review the highlighted cases before processing. Duplicate submissions are not deleted automatically.")

exclude_ids = st.multiselect(
    "Exclude submissions",
    wide["Response_ID"].astype(str).tolist(),
    help="Use this for accidental duplicate submissions or an invalid index-number entry you do not want analysed.",
)

remaining = wide[~wide["Response_ID"].astype(str).isin(exclude_ids)].copy()
try:
    processable = reaudit_responses_by_manifest(remaining, active_session_manifests)
except Exception as exc:
    st.error(f"Could not re-check the remaining submissions: {type(exc).__name__}: {exc}")
    st.stop()

unresolved = processable[processable["Needs_Review"]].copy() if not processable.empty else processable.copy()
if not unresolved.empty:
    st.warning(
        f"{len(unresolved)} remaining submission{'s' if len(unresolved) != 1 else ''} still need review. "
        "Exclude invalid entries or one copy of each duplicate before processing; nothing ambiguous will be scored automatically."
    )
    with st.expander("Remaining submissions that block processing", expanded=True):
        st.dataframe(unresolved[review_cols], use_container_width=True, hide_index=True)

processable = processable[~processable["Needs_Review"]].copy() if not processable.empty else processable
can_process = (not processable.empty) and unresolved.empty
if st.button("Process valid responses", type="primary", disabled=not can_process, use_container_width=True):
    manifest_by_form = {m["form_id"]: m for m in active_session_manifests}
    long_frames = []
    for form_id, group in processable.groupby("Form_ID"):
        manifest = manifest_by_form[form_id]
        qids = list(manifest["question_map_internal_to_google"].keys())
        long_frames.append(api_responses_wide_to_long(group, qids))
    long = pd.concat(long_frames, ignore_index=True)
    long = option_text_to_letter(long, bank)
    scored = score_responses(long, bank)
    lo, _, _ = load_concept_master()
    scored_enriched = add_curriculum_to_scored(scored, lo)
    lo_summary = add_curriculum_wording(student_lo_summary(scored), lo)
    topic_summary = student_topic_summary(scored)
    topic_lookup = lo[["Topic_Code", "Official Topic"]].drop_duplicates("Topic_Code")
    topic_summary = topic_summary.merge(topic_lookup, on="Topic_Code", how="left", validate="many_to_one")
    class_summary = rank_class_revision_priorities(class_lo_summary(scored))

    st.session_state["scored_enriched"] = scored_enriched
    st.session_state["student_lo_summary"] = lo_summary
    st.session_state["student_topic_summary"] = topic_summary
    st.session_state["class_summary"] = class_summary
    st.session_state["active_diagnostic_id"] = selected_id

if "student_lo_summary" not in st.session_state:
    st.stop()

lo_summary = st.session_state["student_lo_summary"]
topic_summary = st.session_state["student_topic_summary"]
class_summary = st.session_state["class_summary"]
scored_enriched = st.session_state["scored_enriched"]

st.divider()
st.subheader("Results")
class_names = sorted(lo_summary["Class_Name"].dropna().unique())
view_class = st.selectbox("View class", ["All classes"] + class_names)

view_lo = lo_summary if view_class == "All classes" else lo_summary[lo_summary["Class_Name"].eq(view_class)]
view_topic = topic_summary if view_class == "All classes" else topic_summary[topic_summary["Class_Name"].eq(view_class)]
view_class_summary = class_summary if view_class == "All classes" else class_summary[class_summary["Class_Name"].eq(view_class)]

student_count = view_lo["Pupil_Key"].nunique()
mean_accuracy = (
    scored_enriched[scored_enriched["Class_Name"].eq(view_class)]["Correct"].mean() * 100
    if view_class != "All classes" else scored_enriched["Correct"].mean() * 100
)
c1, c2 = st.columns(2)
with c1: metric_card("Pupils", student_count)
with c2: metric_card("Question accuracy", f"{mean_accuracy:.1f}%")

st.markdown("### Concepts to revisit first")
st.dataframe(
    view_class_summary.head(20),
    use_container_width=True,
    hide_index=True,
)

with st.expander("Pupil topic evidence"):
    st.dataframe(view_topic, use_container_width=True, hide_index=True)
with st.expander("Pupil learning-outcome evidence"):
    st.dataframe(view_lo, use_container_width=True, hide_index=True)
with st.expander("Question-level detail"):
    detail = scored_enriched if view_class == "All classes" else scored_enriched[scored_enriched["Class_Name"].eq(view_class)]
    st.dataframe(detail, use_container_width=True, hide_index=True)

excel_bytes = dataframe_to_excel_bytes({
    "Pupil_LO": lo_summary,
    "Pupil_Topic": topic_summary,
    "Question_Detail": scored_enriched,
    "Class_LO": class_summary,
})
st.download_button(
    "Download analysis workbook",
    excel_bytes,
    file_name=f"{st.session_state.get('active_diagnostic_id','science_diagnostic')}_analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)

anonymised = anonymise_student_data(lo_summary)
st.download_button(
    "Download anonymised summary",
    anonymised.to_csv(index=False).encode("utf-8-sig"),
    file_name="anonymised_diagnostic_summary.csv",
    mime="text/csv",
    use_container_width=True,
)
