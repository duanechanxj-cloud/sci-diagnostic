# V2.4.1 changes

## Teacher UI

- Fixed Home workflow alignment with one true equal-sized 2x2 CSS grid.
- Renamed `Parent Reports` to `Reports (AI-enabled)`.
- Renamed all current Question Bank authoring UI to `Gemini Notebook`.
- Added P3/P4/P5/P6/All Question Bank filtering plus topic/status/use/probe filters.
- Kept Checkpoint as teacher-entered free text and added examples explaining its purpose.

## Google Forms

- Replaced free-text class index entry with a class-range dropdown.
- Backend range and duplicate-submission validation remains in place.

## Reports

- Replaced the oversized horizontal bar chart with a compact performance matrix and thin 0-100 dot track.
- Added concise topic display labels so curriculum titles no longer consume the visual.
- Report body/table font size is 10 pt.
- Calibri is preferred; Carlito is used only if Calibri is unavailable in the runtime.
- Renamed AI guidance to `Suggested next steps`; removed `How parents can help`.
- Updated Gemini structured output and prompt for teacher-or-parent use and strict brevity.
- Enforced a maximum of two pages per pupil after PDF generation.
- Gemini API key remains session-only and is never written to disk by the app.
- Report ZIP is now `science_diagnostic_reports.zip` or includes the checkpoint label.

## Reliability

- Added explicit `pypdf` dependency for page-limit verification.
- Added tests for dropdown index construction, report page limit, new report wording, ZIP naming, Gemini Notebook pack terminology and UI contracts.
