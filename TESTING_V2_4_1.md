# V2.4.1 manual end-to-end retest

## 1. Local tests

```bash
python -m pytest -q
```

Expected packaged result: all tests pass.

## 2. Visual pass

Launch Streamlit and verify:

- dark theme is readable;
- Home workflow cards form an aligned equal-sized 2x2 grid;
- no clipped headings/text;
- Question Bank defaults to P3 and filters correctly;
- current terminology says Gemini Notebook and Reports (AI-enabled).

## 3. Google connection/classes

Confirm migrated Google connection and test classes are present.

## 4. Question Bank

Upload `data/templates/V2_4_1_system_test_questions.csv`, save, and verify all three questions validate.

## 5. Create Diagnostic

Create a diagnostic for two test classes. Confirm:

- one Google Form and one QR per class;
- the first Form question is an index-number dropdown;
- dropdown values match that class's configured range;
- email is not collected.

## 6. Submit test responses

Use the same index number in two different classes and submit deliberately different answer patterns.

## 7. Analyse Responses

Verify class + index separation, expected scoring and duplicate handling.

## 8. Reports (AI-enabled)

Enter a checkpoint such as `WA3 Revision`. If using Gemini, paste an API key for the current session only.

Verify each PDF:

- uses the compact topic performance matrix/dot track;
- uses concise topic labels;
- has no `How parents can help` section;
- uses `Suggested next steps` when Gemini returns them;
- stays within two pages;
- ZIP name is `science_diagnostic_reports_WA3_Revision.zip`.

Quit and restart Streamlit to confirm the Gemini API key is not persisted by the app.
