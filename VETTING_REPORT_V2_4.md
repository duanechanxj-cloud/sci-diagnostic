# V2.4 vetting report

Date: 2026-08-30

## Automated result

**42 tests passed.**

Command:

```bash
python -m pytest -q
```

Result:

```text
.......................................... [100%]
42 passed
```

## Additional checks

### Python syntax / import-time compilation

```bash
python -m compileall -q app src scripts
```

Passed.

### Packaged Concept Master integrity

Verified that:

- LO_ID values are unique;
- every LO Topic_Code exists in Topic_Index;
- levels are within P3-P6;
- the packaged Concept Master is byte-identical to the latest project mastery-map workbook used for this build.

### Packaged clean system-test questions

`data/templates/V2_4_system_test_questions.csv` was validated against the real packaged Concept Master.

Result:

- 3 rows;
- 0 validation issues;
- all 3 eligible when Diagnostic type = Topic;
- all 3 eligible when Diagnostic type = Pre-WA;
- all 3 eligible when Diagnostic type = EOY.

### Diagnostic package integration

A diagnostic ZIP was generated from the packaged system-test questions and checked for the expected files:

- `student_questions.csv`
- `answer_key.csv`
- `diagnostic_blueprint.csv`
- `google_forms_ready.csv`
- `diagnostic_manifest.json`

### Google Forms logic

Mocked API tests verify:

- public responder permission payload;
- class/index response mapping;
- empty-response handling;
- OAuth Desktop JSON validation;
- Form creation starts unpublished;
- class index field is created;
- Google question IDs map back to internal Question_IDs;
- publish state is applied;
- duplicate answer options fail before the Form-create API is called;
- QR generation returns a valid PNG.

### Response/scoring pipeline

Tests verify:

- the same index number in two classes creates different Pupil_Key values;
- duplicate submissions are flagged within a class;
- duplicates are cleared only after one copy is excluded and responses are re-audited;
- each class uses its own allowed index range;
- Google option text maps back to A/B/C/D;
- local scoring is correct;
- class/index identifiers are removed from anonymised exports and Gemini evidence;
- parent PDF filenames do not collide across classes.

### Question Bank safeguards

Tests verify:

- empty editor placeholder rows do not become fake questions;
- missing IDs are assigned locally;
- missing status defaults to Candidate on import;
- missing Diagnostic_Use defaults to Any on import;
- invalid Diagnostic_Use is rejected;
- Level and Topic_Code must match LO_ID;
- duplicate option text is rejected case-insensitively;
- the NotebookLM template pack contains the exact expected files/columns.

### UI contract checks

Static tests verify:

- Streamlit base theme is dark;
- main text/background contrast exceeds WCAG AAA normal-text contrast;
- muted text/background contrast exceeds WCAG AA normal-text contrast;
- 16 px base font;
- safe top padding;
- 1440 px responsive maximum content width;
- stretch alignment for columns;
- minimum 46 px controls;
- shared box-sizing/width/height rules for card families.

## What cannot be fully tested inside the build environment

The build container does not contain Streamlit, and network access is unavailable to install it, so a true browser-render screenshot of V2.4 could not be produced here. The UI was therefore checked through source/configuration contracts rather than a live Streamlit renderer.

The build environment also does not contain the teacher's Google OAuth token, so live Google Form creation/fetch cannot be executed here. API request/response behaviour is covered using fake services; the live account workflow remains part of `TESTING_V2_4.md` on the teacher's Mac.

Similarly, no live Gemini call was made because no API key is bundled or stored in the project. Privacy preparation, payload exclusion and report fallback logic are tested locally.

## Release decision

V2.4 is suitable for a fresh private-pilot retest on macOS. Start with `data/templates/V2_4_system_test_questions.csv` and follow `TESTING_V2_4.md` before importing real curriculum-grounded questions.
