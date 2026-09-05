# V2.4.1 vetting report

## Automated tests

Final source tree result:

```text
46 passed
```

Coverage includes:

- Concept Master / Question Bank reference integrity;
- controlled-value validation;
- Gemini Notebook template-pack contents;
- Google Forms request construction and response mapping;
- class/index separation and duplicate-response auditing;
- index-number dropdown options generated from class range;
- local scoring and anonymisation;
- report ZIP naming;
- compact report wording/layout contracts;
- two-page PDF limit on a representative larger P3 report;
- session-only Gemini API-key UI/config contract;
- dark UI alignment/legibility source contracts.

## Additional checks

- `python -m compileall -q src app scripts` passed.
- V2.4 -> V2.4.1 migration helper smoke test passed for classes, OAuth client/token and Question Bank.
- Final packaged ZIP was extracted into a fresh folder and all 46 tests passed again.
- Google Form creation fake-service tests confirm the index field is a `DROP_DOWN` with the configured class range.
- Representative report with 3 concept rows generated as one page and was rendered to PNG for visual inspection.
- Representative larger P3 report with 4 topics and 12 concept rows generated as two pages and both pages were rendered for visual inspection.
- Rendered reports showed no clipped text, overlapping elements or oversized topic labels.

## PDF typography note

V2.4.1 prefers **Calibri** and searches the host system for the installed font. The build container does not contain proprietary Calibri fonts, so vetting renders used the metric-compatible **Carlito** fallback. No font files are bundled with the project. On a Mac where Calibri is installed, the report generator selects Calibri automatically; the Reports page displays the resolved family if it has to fall back.

Body/table report text is fixed at **10 pt**. The report title is intentionally larger for hierarchy.

## Live-service limitation

The build environment does not contain Streamlit, so the final Streamlit browser UI cannot be live-rendered here. UI changes were checked through source/config contracts and must still receive the normal visual pass on the user's Mac.

Live Google creation/fetch and live Gemini generation require the user's authorised credentials/API key. API request construction and privacy transformations were tested locally without those credentials.

## V2.4.1 report changes verified

- compact performance matrix + thin 0-100 dot track;
- short topic display labels;
- `Suggested next steps` instead of `How parents can help`;
- no generic parent-only fallback guidance when Gemini is disabled/fails;
- maximum two pages per pupil enforced after PDF generation;
- checkpoint-aware `science_diagnostic_reports_*.zip` naming.
