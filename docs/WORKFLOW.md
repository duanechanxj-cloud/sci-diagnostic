# Workflow - V2.4.1

## Build

MOE curriculum -> Gemini Notebook grounded candidates -> teacher moderation -> Approved Master Question Bank.

## Launch

Select scope -> select approved questions -> choose classes -> create missing class Forms -> display/download class QR codes.

Pupil workflow:

```text
Scan class QR -> select index number from dropdown -> answer MCQs -> submit
```

The pupil does not select a class and does not provide a name or email address.

## Analyse

Select Diagnostic_ID -> fetch selected class Forms -> audit index numbers -> review duplicates -> optionally exclude submissions -> local scoring -> class and pupil evidence.

## Report

Select classes -> enter a free-text checkpoint if useful -> optionally send identity-stripped question evidence to Gemini -> generate local PDFs labelled only by class + index number. Reports are constrained to two pages per pupil.
