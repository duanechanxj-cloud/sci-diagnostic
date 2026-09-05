from pathlib import Path
import hashlib
import io
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.auth import is_admin_user
from src.curriculum import load_concept_master
from src.question_bank import (
    VALID_OPTIONS,
    VALID_PROBE_TYPES,
    load_question_bank,
    delete_all_questions,
    delete_questions,
    make_gemini_notebook_template_pack,
    make_question_bank_template_csv,
    merge_imported_questions,
    normalize_question_bank,
    prepare_multiple_imports,
    save_question_bank,
    set_question_review_status,
    set_questions_review_status,
    update_question_record,
    validate_question_bank,
)
from src.ui import page_header, metric_card
from src.runtime import persist_runtime_state



user = st.session_state.get("auth_user", {})
if not is_admin_user(user):
    st.error("Admin access is required for this page.")
    st.stop()

page_header(
    "Question Bank",
    "Bring in candidate questions quickly, approve them in batches, and manage the permanent P3-P6 bank in one place.",
)

learning_outcomes, _, topics = load_concept_master()
existing_bank = load_question_bank()


COLUMN_CONFIG = {
    "Correct_Option": st.column_config.SelectboxColumn(
        "Correct_Option", options=sorted(VALID_OPTIONS), required=True, width="small"
    ),
    "Probe_Type": st.column_config.SelectboxColumn(
        "Probe_Type", options=sorted(VALID_PROBE_TYPES), required=True, width="medium"
    ),
    "Diagnostic_Use": st.column_config.SelectboxColumn(
        "Diagnostic_Use", options=["Any", "Topic", "Pre-WA", "EOY"], required=True, width="small"
    ),
    "Review_Status": st.column_config.SelectboxColumn(
        "Review_Status", options=["Candidate", "Approved", "Rejected", "Retired"], required=True, width="small"
    ),
    "Times_Used": st.column_config.NumberColumn("Times_Used", min_value=0, step=1, width="small"),
}


def _validation_counts(bank: pd.DataFrame):
    validation = validate_question_bank(bank, learning_outcomes)
    invalid = int((~validation["Valid"]).sum()) if not validation.empty else 0
    return validation, invalid


def _merge_visible_edits(full_bank: pd.DataFrame, original_view: pd.DataFrame, edited_view: pd.DataFrame):
    visible_ids = set(original_view["Question_ID"].astype(str))
    remaining = full_bank[~full_bank["Question_ID"].astype(str).isin(visible_ids)].copy()
    return normalize_question_bank(pd.concat([remaining, normalize_question_bank(edited_view)], ignore_index=True))


def _approved_valid_ids(bank: pd.DataFrame, candidate_ids):
    candidate_ids = set(str(qid) for qid in candidate_ids)
    if not candidate_ids:
        return []
    validation = validate_question_bank(bank, learning_outcomes)
    valid_ids = set(validation.loc[validation["Valid"], "Question_ID"].astype(str))
    return sorted(candidate_ids & valid_ids)


import_tab, manage_tab = st.tabs(["Import & Review", "Manage Question Bank"])


with import_tab:
    st.subheader("Gemini Notebook authoring pack")
    st.caption(
        "Use this pack with the official syllabus and TLGs in Gemini Notebook. It contains the exact CSV columns, "
        "valid controlled values, and official learning-outcome IDs accepted by the importer."
    )

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Download Gemini Notebook template pack",
            make_gemini_notebook_template_pack(learning_outcomes, topics),
            file_name="Science_Diagnostic_Gemini_Notebook_Template_Pack.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )
    with d2:
        st.download_button(
            "Download blank CSV only",
            make_question_bank_template_csv(),
            file_name="question_bank_template.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.divider()
    st.subheader("Import candidate questions")
    st.caption(
        "You can upload several CSV files at once. The app combines them into one review batch and assigns any missing Question_IDs safely."
    )

    if "qb_uploader_version" not in st.session_state:
        st.session_state["qb_uploader_version"] = 0

    uploads = st.file_uploader(
        "Import one or more question-bank CSV files",
        type=["csv"],
        accept_multiple_files=True,
        key=f"qb_multi_uploader_{st.session_state['qb_uploader_version']}",
    )
    append_mode = st.checkbox(
        "Append imported questions to the existing bank",
        value=True,
        help="Leave this on for normal use. Turn it off only when you intentionally want this uploaded batch to replace the whole bank.",
    )

    import_batch = normalize_question_bank(pd.DataFrame())
    if uploads:
        try:
            file_parts = []
            frames = []
            for uploaded in uploads:
                payload = uploaded.getvalue()
                file_parts.append(uploaded.name.encode("utf-8") + b"\0" + payload)
                frames.append(pd.read_csv(io.BytesIO(payload), dtype=str).fillna(""))

            existing_id_signature = "|".join(sorted(existing_bank["Question_ID"].astype(str))).encode("utf-8")
            batch_hash = hashlib.sha256(b"\n".join(file_parts) + b"\n" + existing_id_signature).hexdigest()
            if st.session_state.get("qb_import_batch_hash") != batch_hash:
                prepared = prepare_multiple_imports(frames, existing_bank=existing_bank)
                st.session_state["qb_import_batch_hash"] = batch_hash
                st.session_state["qb_import_rows"] = prepared.to_dict(orient="records")

            import_batch = normalize_question_bank(pd.DataFrame(st.session_state.get("qb_import_rows", [])))
        except Exception as exc:
            st.error(f"Could not read the uploaded CSV batch: {type(exc).__name__}: {exc}")
            import_batch = normalize_question_bank(pd.DataFrame())

    if not import_batch.empty:
        st.success(
            f"Loaded {len(import_batch)} candidate question{'s' if len(import_batch) != 1 else ''} "
            f"from {len(uploads)} CSV file{'s' if len(uploads) != 1 else ''}. Nothing is written to the permanent bank until Save All."
        )

        edited_import = st.data_editor(
            import_batch,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            height=560,
            column_config=COLUMN_CONFIG,
            disabled=["Question_ID", "Times_Used", "Last_Used", "Approved_Date", "Approved_By"],
            key=f"qb_import_editor_{st.session_state.get('qb_import_batch_hash', 'none')}",
        )
        edited_import = normalize_question_bank(edited_import)

        batch_validation, batch_invalid = _validation_counts(edited_import)
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            metric_card("Files", len(uploads), "Uploaded together")
        with m2:
            metric_card("Questions", len(edited_import), "In this import batch")
        with m3:
            metric_card("Candidates", int(edited_import["Review_Status"].eq("Candidate").sum()), "Ready for moderation")
        with m4:
            metric_card("Validation issues", batch_invalid, "Fix before approval")

        if batch_invalid:
            st.warning("Questions with validation issues will not be approved. You can still edit them in the table above.")
            with st.expander("Show validation issues"):
                st.dataframe(batch_validation[~batch_validation["Valid"]], use_container_width=True, hide_index=True)
        else:
            st.success("All questions in this import batch pass validation.")

        candidate_ids = edited_import.loc[edited_import["Review_Status"].eq("Candidate"), "Question_ID"].astype(str).tolist()
        approvable_ids = _approved_valid_ids(edited_import, candidate_ids)

        a1, a2 = st.columns(2)
        with a1:
            approve_all_clicked = st.button(
                "Approve All",
                type="primary",
                use_container_width=True,
                disabled=not approvable_ids,
                help="Marks every valid Candidate in this uploaded batch as Approved. Use Save All to write the batch to the permanent bank.",
                key="qb_import_approve_all",
            )
        with a2:
            save_all_clicked = st.button(
                "Save All",
                use_container_width=True,
                help="Saves every question and edit in this import batch to the permanent Question Bank.",
                key="qb_import_save_all",
            )

        if approve_all_clicked:
            updated_batch = set_questions_review_status(edited_import, approvable_ids, "Approved")
            st.session_state["qb_import_rows"] = updated_batch.to_dict(orient="records")
            st.toast(f"Approved {len(approvable_ids)} valid candidate question(s). Click Save All to commit the batch.")
            st.rerun()

        if save_all_clicked:
            proposed = (
                merge_imported_questions(existing_bank, edited_import, overwrite_existing=False)
                if append_mode
                else edited_import
            )
            validation, invalid = _validation_counts(proposed)
            if invalid:
                st.error("Save All was blocked because the resulting Question Bank has validation issues.")
                with st.expander("Show blocking validation issues", expanded=True):
                    st.dataframe(validation[~validation["Valid"]], use_container_width=True, hide_index=True)
            else:
                before = len(existing_bank)
                save_question_bank(proposed)
                persist_runtime_state()
                after = len(proposed)
                added = max(0, after - before) if append_mode else after
                st.session_state.pop("qb_import_batch_hash", None)
                st.session_state.pop("qb_import_rows", None)
                st.session_state["qb_uploader_version"] += 1
                st.toast(f"Question Bank saved. {added} question(s) added from this batch.")
                st.rerun()
    else:
        st.info("Upload one or more CSV files to start a batch review.")


with manage_tab:
    # Reload from disk inside the management tab so a just-saved import appears immediately after rerun.
    bank = load_question_bank()
    st.subheader("Question Bank management")
    st.caption(
        "Search, filter and edit the permanent bank. Approve All applies only to the valid Candidate questions currently visible after filtering."
    )

    if bank.empty:
        st.info("The permanent Question Bank is empty. Import candidate CSV files in the Import & Review tab first.")
    else:
        search_text = st.text_input(
            "Search questions",
            placeholder="Question text, Question_ID, LO_ID, topic or teacher notes",
            key="qb_manage_search",
        ).strip().casefold()

        f1, f2, f3, f4, f5 = st.columns(5)
        with f1:
            level_filter = st.selectbox("Level", ["P3", "P4", "P5", "P6", "All"], index=4, key="qb_manage_level")

        level_view = bank if level_filter == "All" else bank[bank["Level"].eq(level_filter)]
        topic_options = ["All"] + sorted(x for x in level_view["Topic_Code"].dropna().astype(str).unique() if x)
        with f2:
            topic_filter = st.selectbox("Topic", topic_options, key="qb_manage_topic")
        with f3:
            status_filter = st.selectbox(
                "Review status", ["All", "Candidate", "Approved", "Rejected", "Retired"], key="qb_manage_status"
            )
        with f4:
            diagnostic_filter = st.selectbox(
                "Diagnostic use", ["All", "Any", "Topic", "Pre-WA", "EOY"], key="qb_manage_use"
            )
        with f5:
            probe_filter = st.selectbox("Probe type", ["All"] + sorted(VALID_PROBE_TYPES), key="qb_manage_probe")

        mask = pd.Series(True, index=bank.index)
        if level_filter != "All":
            mask &= bank["Level"].eq(level_filter)
        if topic_filter != "All":
            mask &= bank["Topic_Code"].eq(topic_filter)
        if status_filter != "All":
            mask &= bank["Review_Status"].eq(status_filter)
        if diagnostic_filter != "All":
            mask &= bank["Diagnostic_Use"].eq(diagnostic_filter)
        if probe_filter != "All":
            mask &= bank["Probe_Type"].eq(probe_filter)
        if search_text:
            searchable_cols = ["Question_ID", "Question_Text", "LO_ID", "Topic_Code", "TLG_Key_Idea_Ref", "Teacher_Notes"]
            search_mask = pd.Series(False, index=bank.index)
            for col in searchable_cols:
                search_mask |= bank[col].fillna("").astype(str).str.casefold().str.contains(search_text, regex=False)
            mask &= search_mask

        view = bank.loc[mask].copy()
        st.caption(f"Showing {len(view)} of {len(bank)} question(s). Question_ID remains locked as the stable record key.")

        edited_view = st.data_editor(
            view,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            height=590,
            column_config=COLUMN_CONFIG,
            disabled=["Question_ID", "Approved_Date", "Approved_By"],
            key="v245_question_bank_manager",
        )
        edited_view = normalize_question_bank(edited_view)
        edited_bank = _merge_visible_edits(bank, view, edited_view)
        validation, invalid = _validation_counts(edited_bank)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Visible questions", len(edited_view), f"{len(edited_bank)} in the master bank")
        with c2:
            metric_card("Candidates", int(edited_bank["Review_Status"].eq("Candidate").sum()), "Waiting for review")
        with c3:
            metric_card("Approved", int(edited_bank["Review_Status"].eq("Approved").sum()), "Eligible for diagnostics")
        with c4:
            metric_card("Validation issues", invalid, "Must be fixed before Save All")

        if invalid:
            st.warning("There are validation issues in the working bank. Fix them before Save All.")
            with st.expander("Show validation issues"):
                st.dataframe(validation[~validation["Valid"]], use_container_width=True, hide_index=True)

        visible_candidate_ids = edited_view.loc[
            edited_view["Review_Status"].eq("Candidate"), "Question_ID"
        ].astype(str).tolist()
        approvable_visible_ids = _approved_valid_ids(edited_bank, visible_candidate_ids)

        b1, b2, b3 = st.columns(3)
        with b1:
            approve_visible_clicked = st.button(
                "Approve All",
                type="primary",
                use_container_width=True,
                disabled=not approvable_visible_ids,
                help="Approves all valid Candidate questions currently visible under your filters and saves them immediately, including any current table edits.",
                key="qb_manage_approve_all",
            )
        with b2:
            save_bank_clicked = st.button(
                "Save All",
                use_container_width=True,
                disabled=bool(invalid),
                help="Saves every edit currently shown in the management table.",
                key="qb_manage_save_all",
            )
        with b3:
            st.download_button(
                "Download bank backup",
                edited_bank.to_csv(index=False).encode("utf-8-sig"),
                file_name="master_question_bank.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.markdown("#### Selection & deletion")
        st.caption("Selection is explicit. Delete Selected only removes Question_IDs you have selected; Delete All always targets the entire bank.")
        selected_ids = set(st.session_state.get("qb_manage_selected_ids", []))
        visible_ids = set(edited_view["Question_ID"].astype(str))
        selected_visible = sorted(selected_ids & visible_ids)

        s1, s2 = st.columns(2)
        with s1:
            if st.button("Select All", use_container_width=True, disabled=not visible_ids, key="qb_select_all_visible"):
                st.session_state["qb_manage_selected_ids"] = sorted(selected_ids | visible_ids)
                st.rerun()
        with s2:
            if st.button("Deselect All", use_container_width=True, disabled=not selected_ids, key="qb_deselect_all"):
                st.session_state["qb_manage_selected_ids"] = []
                st.rerun()

        selected_choices = st.multiselect(
            "Selected questions",
            options=edited_view["Question_ID"].astype(str).tolist(),
            default=selected_visible,
            format_func=lambda qid: f"{qid} — {str(edited_view.loc[edited_view['Question_ID'].astype(str).eq(qid), 'Question_Text'].iloc[0])[:80]}",
            key="qb_manage_selection_picker",
        )
        outside_visible = selected_ids - visible_ids
        st.session_state["qb_manage_selected_ids"] = sorted(outside_visible | set(selected_choices))
        selected_ids = set(st.session_state["qb_manage_selected_ids"])
        st.caption(f"{len(selected_ids)} question(s) selected across the bank.")

        delete_confirm = st.checkbox(
            f"Confirm deletion of {len(selected_ids)} selected question(s)",
            value=False,
            disabled=not selected_ids,
            key="qb_delete_selected_confirm",
        )
        if st.button(
            "Delete Selected",
            use_container_width=True,
            disabled=(not selected_ids or not delete_confirm),
            key="qb_delete_selected",
        ):
            updated = delete_questions(edited_bank, selected_ids)
            save_question_bank(updated)
            persist_runtime_state()
            st.session_state["qb_manage_selected_ids"] = []
            st.toast(f"Deleted {len(selected_ids)} selected question(s).")
            st.rerun()

        with st.expander("Delete entire Question Bank"):
            st.warning("This removes every question in the master bank. Download a backup first.")
            delete_phrase = st.text_input("Type DELETE ALL to continue", key="qb_delete_all_phrase")
            if st.button(
                "Delete All",
                use_container_width=True,
                disabled=(delete_phrase != "DELETE ALL"),
                key="qb_delete_all",
            ):
                save_question_bank(delete_all_questions(edited_bank))
                persist_runtime_state()
                st.session_state["qb_manage_selected_ids"] = []
                st.toast("The Question Bank is now empty.")
                st.rerun()

        if approve_visible_clicked:
            updated = set_questions_review_status(edited_bank, approvable_visible_ids, "Approved")
            check, check_invalid = _validation_counts(updated)
            if check_invalid:
                st.error("Approve All was blocked because the working bank contains validation issues.")
            else:
                save_question_bank(updated)
                persist_runtime_state()
                st.toast(f"Approved and saved {len(approvable_visible_ids)} visible candidate question(s).")
                st.rerun()

        if save_bank_clicked:
            save_question_bank(edited_bank)
            persist_runtime_state()
            st.toast("All Question Bank edits were saved.")
            st.rerun()

        st.divider()
        st.subheader("Inspect or edit one question")
        st.caption("Use this detailed view when a question needs more careful wording or metadata changes than the table is comfortable for.")

        if view.empty:
            st.info("No questions match the current filters.")
        else:
            question_labels = {
                str(row["Question_ID"]): f"{row['Question_ID']} — {str(row['Question_Text'])[:105]}"
                for _, row in edited_view.iterrows()
            }
            selected_qid = st.selectbox(
                "Question",
                options=list(question_labels),
                format_func=lambda qid: question_labels[qid],
                key="qb_manage_selected_question",
            )
            selected = edited_bank.loc[edited_bank["Question_ID"].eq(selected_qid)].iloc[0]

            with st.container(border=True):
                meta1, meta2, meta3, meta4 = st.columns(4)
                meta1.caption(f"**Status:** {selected['Review_Status']}")
                meta2.caption(f"**Level:** {selected['Level']}")
                meta3.caption(f"**Topic:** {selected['Topic_Code']}")
                meta4.caption(f"**LO:** {selected['LO_ID']}")
                st.markdown(f"**{selected['Question_Text']}**")
                for letter in "ABCD":
                    suffix = "  ✓" if letter == selected["Correct_Option"] else ""
                    st.write(f"{letter}. {selected[f'Option_{letter}']}{suffix}")
                if selected["Answer_Explanation"]:
                    st.caption(f"Answer explanation: {selected['Answer_Explanation']}")

            action1, action2, action3 = st.columns(3)
            with action1:
                approve_one = st.button(
                    "Approve",
                    type="primary",
                    use_container_width=True,
                    disabled=selected["Review_Status"] == "Approved",
                    key="qb_manage_approve_one",
                )
            with action2:
                reject_one = st.button(
                    "Reject",
                    use_container_width=True,
                    disabled=selected["Review_Status"] == "Rejected",
                    key="qb_manage_reject_one",
                )
            with action3:
                edit_one = st.button("Edit", use_container_width=True, key="qb_manage_edit_one")

            selected_check = validate_question_bank(
                edited_bank.loc[edited_bank["Question_ID"].eq(selected_qid)], learning_outcomes
            )
            selected_valid = bool(not selected_check.empty and selected_check.iloc[0]["Valid"])

            if approve_one:
                if not selected_valid:
                    st.error("This question cannot be approved until its validation issues are fixed.")
                else:
                    updated = set_question_review_status(edited_bank, selected_qid, "Approved")
                    save_question_bank(updated)
                    persist_runtime_state()
                    st.toast(f"{selected_qid} approved and saved.")
                    st.rerun()

            if reject_one:
                updated = set_question_review_status(edited_bank, selected_qid, "Rejected")
                save_question_bank(updated)
                persist_runtime_state()
                st.toast(f"{selected_qid} rejected and saved.")
                st.rerun()

            if edit_one:
                st.session_state["qb_manage_edit_qid"] = selected_qid

            if st.session_state.get("qb_manage_edit_qid") == selected_qid:
                st.markdown("#### Detailed edit")
                st.caption("Question_ID stays locked. Changes are validated before being written to the permanent bank.")
                e1, e2, e3 = st.columns(3)
                with e1:
                    levels = ["P3", "P4", "P5", "P6"]
                    level_value = st.selectbox(
                        "Level",
                        levels,
                        index=levels.index(selected["Level"]) if selected["Level"] in levels else 0,
                        key=f"manage_edit_level_{selected_qid}",
                    )
                with e2:
                    topic_value = st.text_input(
                        "Topic code", value=selected["Topic_Code"], key=f"manage_edit_topic_{selected_qid}"
                    )
                with e3:
                    lo_value = st.text_input("LO ID", value=selected["LO_ID"], key=f"manage_edit_lo_{selected_qid}")

                question_value = st.text_area(
                    "Question", value=selected["Question_Text"], key=f"manage_edit_question_{selected_qid}"
                )
                oa, ob = st.columns(2)
                with oa:
                    option_a = st.text_input("Option A", value=selected["Option_A"], key=f"manage_edit_a_{selected_qid}")
                    option_c = st.text_input("Option C", value=selected["Option_C"], key=f"manage_edit_c_{selected_qid}")
                with ob:
                    option_b = st.text_input("Option B", value=selected["Option_B"], key=f"manage_edit_b_{selected_qid}")
                    option_d = st.text_input("Option D", value=selected["Option_D"], key=f"manage_edit_d_{selected_qid}")

                e4, e5, e6 = st.columns(3)
                with e4:
                    correct_options = sorted(VALID_OPTIONS)
                    correct_value = st.selectbox(
                        "Correct option",
                        correct_options,
                        index=correct_options.index(selected["Correct_Option"]) if selected["Correct_Option"] in correct_options else 0,
                        key=f"manage_edit_correct_{selected_qid}",
                    )
                with e5:
                    probe_options = sorted(VALID_PROBE_TYPES)
                    probe_value = st.selectbox(
                        "Probe type",
                        probe_options,
                        index=probe_options.index(selected["Probe_Type"]) if selected["Probe_Type"] in probe_options else 0,
                        key=f"manage_edit_probe_{selected_qid}",
                    )
                with e6:
                    diagnostic_options = ["Any", "Topic", "Pre-WA", "EOY"]
                    diagnostic_value = st.selectbox(
                        "Diagnostic use",
                        diagnostic_options,
                        index=diagnostic_options.index(selected["Diagnostic_Use"]) if selected["Diagnostic_Use"] in diagnostic_options else 0,
                        key=f"manage_edit_use_{selected_qid}",
                    )

                explanation_value = st.text_area(
                    "Answer explanation", value=selected["Answer_Explanation"], key=f"manage_edit_explanation_{selected_qid}"
                )
                key_idea_value = st.text_input(
                    "TLG Key Idea reference", value=selected["TLG_Key_Idea_Ref"], key=f"manage_edit_keyidea_{selected_qid}"
                )
                alternative_value = st.text_input(
                    "Alternative Conception reference",
                    value=selected["Alternative_Conception_Ref"],
                    key=f"manage_edit_alt_{selected_qid}",
                )
                source_value = st.text_input(
                    "Source note", value=selected["Source_Note"], key=f"manage_edit_source_{selected_qid}"
                )
                notes_value = st.text_area(
                    "Teacher notes", value=selected["Teacher_Notes"], key=f"manage_edit_notes_{selected_qid}"
                )

                save_edit, cancel_edit = st.columns(2)
                with save_edit:
                    save_edit_clicked = st.button(
                        "Save question edits", type="primary", use_container_width=True, key="qb_manage_save_detail"
                    )
                with cancel_edit:
                    cancel_edit_clicked = st.button(
                        "Cancel", use_container_width=True, key="qb_manage_cancel_detail"
                    )

                if save_edit_clicked:
                    proposed = update_question_record(edited_bank, selected_qid, {
                        "Level": level_value,
                        "Topic_Code": topic_value,
                        "LO_ID": lo_value,
                        "Question_Text": question_value,
                        "Option_A": option_a,
                        "Option_B": option_b,
                        "Option_C": option_c,
                        "Option_D": option_d,
                        "Correct_Option": correct_value,
                        "Answer_Explanation": explanation_value,
                        "Probe_Type": probe_value,
                        "TLG_Key_Idea_Ref": key_idea_value,
                        "Alternative_Conception_Ref": alternative_value,
                        "Diagnostic_Use": diagnostic_value,
                        "Source_Note": source_value,
                        "Teacher_Notes": notes_value,
                    })
                    check = validate_question_bank(
                        proposed.loc[proposed["Question_ID"].eq(selected_qid)], learning_outcomes
                    )
                    if check.empty or not bool(check.iloc[0]["Valid"]):
                        problems = "Unknown validation error" if check.empty else check.iloc[0]["Problems"]
                        st.error(f"Edits were not saved: {problems}")
                    else:
                        save_question_bank(proposed)
                        persist_runtime_state()
                        st.session_state.pop("qb_manage_edit_qid", None)
                        st.toast(f"{selected_qid} updated and saved.")
                        st.rerun()

                if cancel_edit_clicked:
                    st.session_state.pop("qb_manage_edit_qid", None)
                    st.rerun()
