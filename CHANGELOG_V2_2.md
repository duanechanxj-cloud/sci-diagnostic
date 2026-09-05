# V2.2 changes

- Streamlit is the primary teacher interface; Jupyter remains for development/debugging.
- Removed roster/Student_ID as a normal workflow requirement.
- Pupil label is `First name + surname initial`.
- Google Forms `responseId` becomes local `Response_ID` for each submission.
- Added pupil-label normalisation and duplicate/format review flags.
- Added direct Google Forms API creation from Streamlit.
- Added explicit post-June-2026 Form publishing.
- Added Google Drive published-reader permission so anyone with the QR/link can respond.
- Disabled Form email collection.
- Form is not a Google Quiz; Python scores locally from the approved Master Question Bank.
- Added direct Google Forms response retrieval from Streamlit.
- Saved Google questionId ↔ internal Question_ID manifests locally.
- Added QR generation/download inside Streamlit.
- Parent-report Gemini calls remove Student_Name, Response_ID and Timestamp.
- Updated Gemini 3.7 Flash configuration to use `thinking_level="low"` and removed deprecated sampling parameters.
- Horizontal per-topic pupil chart retained.
- Duplicate pupil labels cannot overwrite PDFs.
- Added current Google setup guide and V2.2 automated tests.
