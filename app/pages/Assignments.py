from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.assignments import clear_assignment_links, delete_assignment, list_assignments
from src.auth import is_admin_user
from src.config import GOOGLE_FORMS_DIR
from src.google_forms_api import make_qr_png
from src.runtime import persist_runtime_state
from src.ui import page_header

page_header(
    "Assignments",
    "Persistent history of class diagnostics. Reopen the pupil Form or retrieve its QR code whenever you need it.",
)

assignments = list_assignments(GOOGLE_FORMS_DIR)
if not assignments:
    st.info("No class diagnostics have been assigned yet. Create a diagnostic and class Form first.")
    st.stop()

levels = sorted({str(a.get("level", "")) for a in assignments if a.get("level")})
classes = sorted({str(a.get("class_name", "")) for a in assignments if a.get("class_name")})
filter_cols = st.columns(2)
with filter_cols[0]:
    level_filter = st.selectbox("Level", ["All"] + levels)
with filter_cols[1]:
    class_filter = st.selectbox("Class / group", ["All"] + classes)

filtered = [
    a for a in assignments
    if (level_filter == "All" or a.get("level") == level_filter)
    and (class_filter == "All" or a.get("class_name") == class_filter)
]

summary_rows = []
for a in filtered:
    topics = a.get("topic_codes", [])
    if isinstance(topics, str):
        topics = [topics]
    summary_rows.append({
        "Assigned": str(a.get("created_at", ""))[:10],
        "Class": a.get("class_name", ""),
        "Diagnostic": a.get("assignment_title", a.get("title", "")),
        "Topics": ", ".join(topics),
        "Pupils": a.get("student_count", a.get("index_max", "")),
        "Questions": a.get("question_count", ""),
        "Launch link": "Available" if a.get("links_available") else "Cleared",
    })
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

st.divider()
labels = {
    str(i): f"{str(a.get('created_at',''))[:10]} · {a.get('class_name','')} · {a.get('assignment_title', a.get('diagnostic_id',''))}"
    for i, a in enumerate(filtered)
}
selected_key = st.selectbox("Open assignment", list(labels), format_func=lambda key: labels[key])
manifest = filtered[int(selected_key)]

st.subheader(manifest.get("assignment_title", manifest.get("title", "Diagnostic")))
c1, c2, c3 = st.columns(3)
c1.metric("Class", manifest.get("class_name", ""))
c2.metric("Pupils", manifest.get("student_count", manifest.get("index_max", "")))
c3.metric("Questions", manifest.get("question_count", ""))

if manifest.get("links_available") and manifest.get("responder_uri"):
    qr = make_qr_png(manifest["responder_uri"])
    left, right = st.columns([1, 2])
    with left:
        st.image(qr, width=240)
        st.download_button(
            "Download QR code",
            qr.getvalue(),
            file_name=f"{manifest.get('diagnostic_id','diagnostic')}_{manifest.get('class_name','class').replace(' ','_')}_QR.png",
            mime="image/png",
            use_container_width=True,
        )
    with right:
        st.link_button("Open pupil Google Form", manifest["responder_uri"], type="primary", use_container_width=True)
        if manifest.get("edit_uri"):
            st.link_button("Open Form in Google Drive", manifest["edit_uri"], use_container_width=True)
        st.caption("The QR code and link remain available here after you log out and return because the assignment manifest is saved in persistent Google Drive state.")
else:
    st.warning("The launch links for this assignment were cleared by an Admin. The assignment history itself is still retained.")

if is_admin_user(st.session_state.get("auth_user", {})):
    st.divider()
    st.subheader("Admin link management")
    st.caption("Clearing links removes the saved QR/Form launch URLs from Sci Diagnostic, but does not delete the assignment record or the Google Form itself.")
    if manifest.get("links_available"):
        confirm = st.checkbox("I want to clear the saved launch links for this assignment.")
        if st.button("Clear assignment links", disabled=not confirm, use_container_width=True):
            clear_assignment_links(manifest, GOOGLE_FORMS_DIR)
            status = persist_runtime_state()
            st.success("Launch links cleared. Assignment history was retained.")
            if status.enabled and "failed" in status.message.lower():
                st.warning(status.message)
            st.rerun()

    st.subheader("Permanent deletion")
    st.caption(
        "This removes the assignment record and its locally stored responses, analysis, and generated artifacts. "
        "It does not delete the Google Form."
    )
    delete_confirm = st.checkbox("I understand that this assignment cannot be restored.")
    if st.button(
        "Delete assignment permanently",
        disabled=not delete_confirm,
        type="secondary",
        use_container_width=True,
    ):
        delete_assignment(manifest, GOOGLE_FORMS_DIR)
        form_id = str(manifest.get("form_id", ""))
        for key in ["v24_raw_responses", "v24_active_manifests"]:
            value = st.session_state.get(key)
            if key == "v24_active_manifests" and isinstance(value, list):
                st.session_state[key] = [m for m in value if str(m.get("form_id", "")) != form_id]
            elif key == "v24_raw_responses" and hasattr(value, "columns") and "Form_ID" in value.columns:
                st.session_state[key] = value[value["Form_ID"].astype(str) != form_id].copy()
        for key in ["scored_enriched", "student_lo_summary", "student_topic_summary", "class_summary"]:
            value = st.session_state.get(key)
            if hasattr(value, "columns") and "Form_ID" in value.columns:
                st.session_state[key] = value[value["Form_ID"].astype(str) != form_id].copy()
        if not st.session_state.get("v24_active_manifests"):
            st.session_state.pop("active_diagnostic_id", None)
        status = persist_runtime_state()
        st.success("Assignment permanently deleted. The Google Form was left unchanged.")
        if status.enabled and "failed" in status.message.lower():
            st.warning(status.message)
        st.rerun()
