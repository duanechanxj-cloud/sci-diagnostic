from pathlib import Path
import sys
import tempfile

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ai_analysis import analyse_student_with_ai, analyse_class_with_ai
from src.ai_ui import render_ai_provider_controls
from src.privacy import strip_local_pupil_identity
from src.reporting import generate_reports_for_class, combine_pdf_files, combined_report_filename, RESOLVED_FONT_FAMILY
from src.teacher_reporting import generate_teacher_class_pdf, teacher_report_filename
from src.ui import page_header, metric_card

page_header(
    "Reports (AI-enabled)",
    "Generate concise pupil diagnostic reports for teacher or parent use. AI is optional and receives anonymous Science evidence only.",
)

use_session = all(k in st.session_state for k in ["student_lo_summary", "student_topic_summary", "scored_enriched"])
if use_session:
    lo_summary = st.session_state["student_lo_summary"]
    topic_summary = st.session_state["student_topic_summary"]
    question_detail = st.session_state["scored_enriched"]
    st.success("Using the diagnostic currently loaded in Streamlit.")
else:
    upload = st.file_uploader("Upload a V2.4.1+ analysis workbook", type=["xlsx"])
    if not upload:
        st.info("Analyse responses first, or upload a previously saved V2.4.1+ analysis workbook.")
        st.stop()
    sheets = pd.read_excel(upload, sheet_name=None)
    required_sheets = {"Pupil_LO", "Pupil_Topic", "Question_Detail"}
    missing = required_sheets - set(sheets)
    if missing:
        st.error(f"Workbook is missing sheets: {sorted(missing)}")
        st.stop()
    lo_summary = sheets["Pupil_LO"]
    topic_summary = sheets["Pupil_Topic"]
    question_detail = sheets["Question_Detail"]

required_cols = {"Response_ID", "Class_Name", "Index_Number", "Pupil_Key"}
for label, frame in [("Pupil_LO", lo_summary), ("Pupil_Topic", topic_summary), ("Question_Detail", question_detail)]:
    if not required_cols.issubset(frame.columns):
        st.error(f"{label} is not a compatible V2.4.1+ class/index-number dataset. Re-process the diagnostic in the current app.")
        st.stop()

class_names = sorted(lo_summary["Class_Name"].dropna().unique())
selected_classes = st.multiselect("Classes", class_names, default=class_names)
lo_selected = lo_summary[lo_summary["Class_Name"].isin(selected_classes)].copy()
topic_selected = topic_summary[topic_summary["Class_Name"].isin(selected_classes)].copy()
detail_selected = question_detail[question_detail["Class_Name"].isin(selected_classes)].copy()
response_ids = lo_selected["Response_ID"].astype(str).drop_duplicates().tolist()

c1, c2 = st.columns(2)
with c1:
    metric_card("Reports", len(response_ids))
with c2:
    metric_card("Classes", len(selected_classes))

report_title = st.text_input("Report title", "Primary Science Learning Diagnostic")
checkpoint = st.text_input(
    "Checkpoint",
    "",
    help="Describe why or when this analysis was done. Examples: Pre-EOY diagnostic, Magnets end-of-topic, Post-intervention recheck, Term 2 review.",
)
st.caption("Checkpoint example: Pre-EOY diagnostic, Magnets end-of-topic, Post-intervention recheck, or Term 2 review.")
include_score = st.checkbox("Show percentages in concept table", value=False)
st.caption("Each pupil report remains capped at two pages. All selected pupil reports and the teacher report are combined into one downloadable PDF.")
if RESOLVED_FONT_FAMILY != "Arial":
    st.caption(f"Arial was not detected in this runtime; the report generator is using {RESOLVED_FONT_FAMILY} as a safe PDF fallback.")

st.divider()
use_ai = st.checkbox("Use AI to write pupil interpretations and teacher class analysis", value=True)
generate_teacher_report = st.checkbox(
    "Include an AI-assisted teacher report for each selected class",
    value=True,
    disabled=not use_ai,
    help="Adds one anonymous class-level AI analysis per selected class. Scores and percentages are calculated locally first.",
)
provider = ""
api_key = ""
model = ""
if use_ai:
    st.info(
        "Pupil reports send only anonymous question-by-question Science evidence. Teacher reports send only anonymous, locally calculated class evidence. "
        "Pupil/class identifiers are not included in the AI prompts."
    )
    policy_ok = st.checkbox(
        "I have confirmed that sending anonymised diagnostic evidence to the selected AI provider is permitted."
    )
    provider, model, api_key = render_ai_provider_controls()
    st.caption("Your API key is session-only and is never saved to disk by Sci Diagnostic.")
else:
    policy_ok = True

can_generate = bool(response_ids) and ((not use_ai) or (policy_ok and bool(api_key.strip())))
if st.button("Generate reports", type="primary", disabled=not can_generate, use_container_width=True):
    analyses = {}
    teacher_analyses = {}
    failures = []
    if use_ai:
        progress = st.progress(0)
        for i, response_id in enumerate(response_ids, start=1):
            rows = detail_selected[detail_selected["Response_ID"].astype(str).eq(response_id)].copy()
            rows_for_api = strip_local_pupil_identity(rows)
            try:
                analyses[response_id] = analyse_student_with_ai(
                    rows_for_api,
                    provider=provider,
                    api_key=api_key,
                    model=model,
                )
            except Exception as exc:
                failures.append(f"{response_id}: {type(exc).__name__}: {exc}")
            progress.progress(i / len(response_ids))

        if generate_teacher_report:
            teacher_progress = st.progress(0)
            for i, class_name in enumerate(selected_classes, start=1):
                class_rows = detail_selected[detail_selected["Class_Name"].astype(str).eq(str(class_name))].copy()
                try:
                    teacher_analyses[str(class_name)] = analyse_class_with_ai(
                        class_rows,
                        provider=provider,
                        api_key=api_key,
                        model=model,
                    )
                except Exception as exc:
                    failures.append(f"Teacher report — {class_name}: {type(exc).__name__}: {exc}")
                teacher_progress.progress(i / max(len(selected_classes), 1))

    try:
        with tempfile.TemporaryDirectory() as tmp:
            paths = generate_reports_for_class(
                lo_selected,
                topic_selected,
                tmp,
                report_title=report_title,
                checkpoint_label=checkpoint,
                include_score=include_score,
                # Kept as the established V2.5 reporting argument for compatibility.
                gemini_analyses=analyses,
            )

            teacher_paths = {}
            if use_ai and generate_teacher_report:
                for class_name, class_analysis in teacher_analyses.items():
                    class_rows = detail_selected[detail_selected["Class_Name"].astype(str).eq(str(class_name))].copy()
                    if class_rows.empty:
                        continue
                    teacher_path = Path(tmp) / teacher_report_filename(class_name, checkpoint)
                    generate_teacher_class_pdf(
                        class_rows,
                        teacher_path,
                        analysis=class_analysis,
                        checkpoint_label=checkpoint,
                    )
                    teacher_paths[str(class_name)] = teacher_path

            # Build one ordered PDF: teacher report first for each class, then pupil
            # reports in class/index-number order. If AI is disabled, the document
            # simply contains all pupil reports.
            ordered_paths = []
            for class_name in selected_classes:
                teacher_path = teacher_paths.get(str(class_name))
                if teacher_path is not None:
                    ordered_paths.append(teacher_path)
                class_prefix = str(class_name).replace(" ", "_")
                ordered_paths.extend([
                    path for path in paths
                    if path.name.startswith(class_prefix + "_")
                ])

            # Fallback for any filenames that do not match the display class name.
            ordered_set = {str(p) for p in ordered_paths}
            ordered_paths.extend([p for p in paths if str(p) not in ordered_set])

            combined_path = Path(tmp) / combined_report_filename(checkpoint)
            combine_pdf_files(ordered_paths, combined_path)
            pdf_bytes = combined_path.read_bytes()
            st.download_button(
                "Download complete report PDF",
                pdf_bytes,
                file_name=combined_report_filename(checkpoint),
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
    except Exception as exc:
        st.error(f"Report generation stopped: {type(exc).__name__}: {exc}")
        st.stop()

    if failures:
        st.warning(
            f"{len(failures)} {provider or 'AI'} call(s) failed. Those PDFs contain the local evidence tables but no invented AI fallback guidance."
        )
        with st.expander(f"{provider or 'AI'} errors"):
            st.code("\n".join(failures))
    elif use_ai:
        extra = " Pupil interpretations and teacher class analysis were generated." if generate_teacher_report else " Pupil interpretations were generated."
        st.success(
            f"{provider} completed the AI analysis without sending pupil identifiers." + extra
        )
