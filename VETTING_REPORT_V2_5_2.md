# V2.5.2 Deployment Candidate Vetting Report

Date: 2026-09-05

## Result

**PASS for code/package deployment candidate**, subject to a final live smoke test with real teacher-owned provider API keys and the chosen hosting environment.

## Regression status

- Automated tests: **71 passed**
- Python compile check: required before packaging
- Standard Bank: **371 unique questions**
- Standard Bank V2.5 SHA-256: `2b7d993776c8b099d871d8c18d667cd257322fb20864596753b8ea563b345c99`
- Both bundled bank CSVs retain that original hash.

## V2.5 features preserved

The V2.5 codebase remains the foundation. The upgrade does not replace:

- curriculum loading/validation;
- class management;
- Question Bank data model and moderation workflow;
- diagnostic auto-build/manual selection;
- Google Forms creation and response retrieval;
- local scoring and analysis;
- PDF report generation;
- Google OAuth runtime handling;
- Google Drive persistent-state snapshots;
- tablet-responsive dark UI;
- legacy Gemini Notebook question-authoring pack.

## Authentication/permissions

V2.5.2 supports exactly two shared account types:

- Teacher
- Admin

Roles are fixed by application code rather than a user-editable role field in Secrets.

Teacher navigation excludes Question Bank and Deployment. Both pages also independently stop non-Admin sessions if accessed directly.

## AI provider layer

Optional report interpretation supports:

- Gemini
- OpenAI
- Claude

All three return into the same `DiagnosticReportAnalysis` schema used by the existing PDF report generator.

The provider/model catalog was reviewed against current official provider documentation on 2026-09-05. Provider model availability can change after release; update `src/ai_analysis.py` if a provider later deprecates a model.

## AI-key privacy

Teacher API keys are entered as masked Streamlit inputs and stored only in `st.session_state` for the current session.

The V2.5.2 code does not write those keys to:

- project files;
- Streamlit Secrets;
- Google Drive state snapshots;
- PDFs;
- exports;
- logs.

Sign-out clears all Streamlit session state, including provider keys.

## Pupil-data privacy

Before an AI call, the existing anonymisation path is preserved. AI evidence excludes:

- Response_ID
- Pupil_Key
- Class_Name/Class_Code
- Index_Number
- timestamp
- email/contact identity

The provider receives only question-by-question Science evidence used for the report interpretation.

## Known release checks still requiring the deployment owner

The automated suite deliberately does not make paid/external provider API calls. Before real pupil use:

1. deploy with the intended hosting service;
2. configure Teacher/Admin password hashes;
3. confirm Google OAuth + persistence;
4. test one anonymous sample report with Gemini;
5. test one anonymous sample report with OpenAI;
6. test one anonymous sample report with Claude;
7. sign out and confirm keys must be re-entered next session.

No live provider credential was embedded in or used to build this release package.
