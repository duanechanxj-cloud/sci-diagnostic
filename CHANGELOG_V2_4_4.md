# V2.4.4

Focused diagnostic-building update built on V2.4.3.

## Auto Build
- Added **Auto Build** as the default question-selection method in Create Diagnostic.
- Teachers choose a target question count for normal Auto Build.
- Python balances the set across available `LO_ID`s before repeating them.
- Within an LO, Auto Build favours less-used questions and different `Probe_Type` values where the bank supports them.
- Auto Build is deterministic and does not use Gemini or another AI model to choose questions.
- Manual selection remains available for full teacher control.

## Cumulative Primary Science assessment
- Create Diagnostic now separates **Assessment level** from **Question levels to include**.
- A P3 assessment may use P3 questions.
- A P4 assessment may use P3-P4 questions.
- A P5 assessment may use P3-P5 questions.
- A P6 assessment may use P3-P6 questions.
- Teachers decide which eligible lower levels to include and then choose any available topics from those levels.
- Class selection and Google Forms still use the Assessment level, so a P6 class can receive a diagnostic containing P3-P6 topics without being treated as a P3/P4/P5 class.

## Comprehensive Auto Build
- **Comprehensive testing** is available with Auto Build and has no fixed question-count cap.
- It aims for at least two independent probes per represented Learning Outcome where available.
- It also includes additional questions needed to represent distinct non-empty TLG Key Idea and Alternative Conception tags already present in the Question Bank.
- It does not blindly include every Approved question.
- The existing Learning Outcome coverage audit remains and now works across mixed lower/current curriculum levels.

## Compatibility
- No new curriculum taxonomy or Question Bank columns were introduced.
- Existing V2.4.3 questions, classes, OAuth data, diagnostics and reporting logic remain compatible.
