# Architecture - V2.5.2

## Core diagnostic rule

One diagnostic question set may serve multiple classes, but each class has its own Google Form and QR code.

```text
Diagnostic_ID
  |-- Class A -> Form A -> QR A -> responses A
  |-- Class B -> Form B -> QR B -> responses B
  `-- Class C -> Form C -> QR C -> responses C
```

Every Form manifest stores `Diagnostic_ID`, `Class_Code`, `Class_Name`, index range, Google Form ID, Google question-ID mapping and responder URL.

## Access model

```text
Login
  |-- Teacher -> normal diagnostic workflow
  `-- Admin   -> Teacher workflow + Question Bank + Deployment
```

There are exactly two shared account types. Password hashes are stored in Streamlit/host Secrets; no account database is used.

## AI report layer

```text
Anonymous scored evidence
        |
        v
Provider adapter
  |-- Gemini
  |-- OpenAI
  `-- Claude
        |
        v
DiagnosticReportAnalysis schema
        |
        v
Existing V2.5 PDF report generator
```

Provider API keys are supplied by the current teacher and remain only in Streamlit session state.

## Data keys

- `LO_ID`: stable curriculum outcome key.
- `Question_ID`: stable Question Bank key.
- `Diagnostic_ID`: one selected diagnostic question set.
- `Form_ID`: one class-specific Google Form.
- `Response_ID`: Google submission identifier.
- `Pupil_Key`: local `Class_Code + Index_Number` convenience key.

`Pupil_Key` is not intended to become a national/school student identifier.

## Interfaces

- VS Code: main development environment.
- Streamlit: teacher-facing product interface.
- Jupyter: optional exploration/debugging.
- Google Forms: pupil-facing response interface; class index number is a dropdown.
- Gemini Notebook: source-grounded candidate question authoring outside the app.
- Gemini/OpenAI/Claude APIs: optional anonymous report-writing assistants.
