# V2.4.3 Vetting Report

## Scope checked
V2.4.3 was built as a targeted update to V2.4.2. Existing scoring, Google Forms, privacy, Gemini report-writing and PDF logic were preserved unless directly affected by the requested changes.

## New behaviour verified
- Question Bank contains teacher-facing **Approve**, **Reject** and **Edit** controls.
- Moderation helpers preserve stable `Question_ID` values and maintain approval dates.
- Uploaded candidate files with blank IDs are prepared once per upload hash so Streamlit reruns do not continually invent new IDs.
- Create Diagnostic no longer exposes a Diagnostic Type selector.
- Teachers can select one or more topics and tick individual Approved questions across those topics.
- Create Diagnostic does not filter the pool by `Diagnostic_Use`.
- **Comprehensive testing** has no question-count cap and uses all Approved questions in the selected topics.
- Comprehensive mode compares selected questions against official Learning Outcomes and reports missing LO coverage.
- TLG Key Idea and Alternative Conception coverage is counted only from explicit Question Bank tags.
- The app explicitly avoids claiming separate Success Criteria coverage because the current Concept Master has no dedicated Success Criteria field; official Details/Sub-points are surfaced for review.
- Report font preference is Arial 10 pt, with Helvetica only as a safe runtime fallback.

## Automated checks
- `python -m compileall -q app src scripts`: passed.
- `pytest -q`: **51 passed**.
- Added tests cover comprehensive LO auditing, moderation helpers, V2.4.3 UI contracts, removal of the Diagnostic Type selector, and Arial report configuration.
- Migration helper from V2.4.2 was smoke-tested with temporary classes, Question Bank and OAuth placeholders.

## Runtime limitation
The build environment used for packaging does not contain Streamlit, so I could not perform a live browser-render test here. The Python modules compile and the automated/static UI-contract tests pass. Live Google Form creation still requires the teacher's authorised Google account and should be sanity-checked on the user's Mac after migration.
