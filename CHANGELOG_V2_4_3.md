# V2.4.3

Focused teacher-workflow update built on V2.4.2.

## Question Bank moderation
- Added teacher-facing **Approve**, **Reject** and **Edit** controls.
- Approve/Reject saves the moderation decision locally immediately.
- Invalid questions cannot be approved until validation issues are fixed.
- Edit keeps `Question_ID` locked and validates changes before saving.
- Imported CSVs are cached by file hash so app-assigned blank Question_IDs remain stable across Streamlit reruns.

## Create Diagnostic redesign
- Removed the visible **Diagnostic type** selector.
- Teachers can choose one or more topics and manually tick any combination of Approved questions.
- `Diagnostic_Use` remains Question Bank metadata but no longer restricts Create Diagnostic.
- Added **Comprehensive testing** mode.
- Comprehensive testing removes the question-count cap and uses every Approved question available in the selected topics.
- Comprehensive mode audits coverage against official Learning Outcomes and shows distinct TLG Key Idea and Alternative Conception tags.
- If an official Learning Outcome has no Approved question, the app warns the teacher before the diagnostic is treated as comprehensive.
- The Concept Master currently has no separate Success Criteria field, so official Details/Sub-points are shown for teacher review rather than falsely claimed as independently tested.

## Reports
- Standardised report font to **Arial 10 pt** where Arial is installed.
- Helvetica is used only as a safe PDF fallback when Arial is unavailable.
- The previous Calibri availability message has been removed.

## Compatibility
- Existing V2.4.2 Question Banks, classes and Google OAuth data remain compatible.
- Google Form manifests keep a backward-compatible internal mode value (`Custom` or `Comprehensive`) without exposing the old diagnostic-type workflow to teachers.
