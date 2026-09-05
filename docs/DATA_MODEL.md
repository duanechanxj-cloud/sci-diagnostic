# Data model — V2.4.1

## Main identifiers

- `LO_ID` — stable curriculum learning-outcome key.
- `Question_ID` — stable approved-question key.
- `Diagnostic_ID` — one selected diagnostic question set.
- `Form_ID` — one Google Form for one class.
- `Response_ID` — Google Forms submission ID.
- `Class_Code` — local short class code.
- `Class_Name` — teacher-facing class label.
- `Index_Number` — pupil-selected class index number.
- `Pupil_Key` — local `Class_Code + Index_Number` key.

## Important distinction

`Response_ID` identifies a submission. `Pupil_Key` identifies the class/index combination used for local analysis. Neither is intended to replace the school's official student identity system.

## Form manifest

Each class Form stores:

- `Diagnostic_ID`
- `Class_Code`, `Class_Name`, `Level`
- allowed index-number range
- Google `form_id`
- responder and edit URLs
- Google question-ID ↔ local `Question_ID` mapping
- publish/access status

Multiple manifests can share one `Diagnostic_ID`, which is how V2.4.1 keeps several classes on the same diagnostic question set while maintaining separate Forms and QR codes.

## Analysis grouping

Pupil summaries retain:

`Response_ID + Class_Code + Class_Name + Index_Number + Pupil_Key`

Class summaries group by class first, then topic/learning outcome.
