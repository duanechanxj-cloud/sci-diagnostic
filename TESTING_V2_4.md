# V2.4 manual end-to-end retest

The automated suite tests local logic and mocked Google API interactions. This checklist verifies the live account/browser workflow on your Mac.

## 1. Start clean

- Open V2.4 in VS Code.
- Activate `.venv`.
- Run Streamlit.
- Confirm the dark UI has no clipped headings and text is readable.

## 2. Reuse safe V2.3 local setup

Run the migration helper if desired, then confirm:

- both test classes appear on **Classes**;
- **Google Connection** says Connected.

## 3. Import known-good test questions

On **Question Bank** upload:

`data/templates/V2_4_system_test_questions.csv`

Expected:

- 3 questions;
- 3 Approved;
- 0 validation issues;
- Save Question Bank enabled.

## 4. Create one diagnostic across two classes

On **Create Diagnostic** choose:

- Level: P3
- Diagnostic type: Topic
- Topics: `P3-DIV-LNL` and `P3-INT-MAG`
- Question count: 3
- Title: `V2.4 Pipeline Test`

Expected: **3 Approved questions match this scope**.

Click **Select questions**, select both test classes, then create the class Forms.

Expected:

- one Google Form per class;
- one QR code per class;
- same 3 Science questions in both Forms;
- pupil Form asks for class index number only;
- no email collection.

## 5. Submit controlled responses

Use the same index number in both classes (for example 2) to prove class separation.

Submit intentionally different answer patterns in the two Forms.

## 6. Fetch and audit

On **Analyse Responses** fetch both Forms.

Expected:

- both classes appear separately;
- same index number produces different `Pupil_Key` values because Class_Code differs;
- deliberately duplicated submissions are flagged;
- processing is blocked until one duplicate is excluded;
- invalid/out-of-range index entries are flagged and block processing until excluded.

## 7. Score and inspect

Process the clean remaining responses.

Expected:

- class-level concept summary;
- pupil topic/LO evidence;
- question-level detail;
- analysis workbook download;
- anonymised summary without class/index/pupil identity.

## 8. Parent report

Generate local PDFs first without Gemini. Then, only if desired/allowed, test the optional Gemini guidance flow and confirm no local identifiers are present in the payload.
