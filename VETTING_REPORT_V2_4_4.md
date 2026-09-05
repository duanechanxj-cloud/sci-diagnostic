# V2.4.4 Vetting Report

## Scope
V2.4.4 was built as a focused update to V2.4.3. Existing Question Bank moderation, Google Forms creation, local scoring/analysis, privacy controls, Gemini report-writing and PDF generation were preserved unless directly affected by diagnostic construction.

## Implemented and checked

### Auto Build
- Added deterministic Python Auto Build to Create Diagnostic.
- Normal Auto Build accepts a teacher-selected target question count.
- Selection round-robins across available `LO_ID`s before repeating an LO.
- Within each LO, less-used questions are preferred and different `Probe_Type` values are represented before same-type repetition where possible.
- Auto Build does not send question selection to Gemini.

### Cumulative assessment scope
- Assessment level is now separate from the curriculum levels supplying questions.
- Supported cumulative scope is P3→P3, P4→P3-P4, P5→P3-P5, P6→P3-P6.
- Teachers explicitly choose which eligible question levels to include.
- Topic selection then shows Approved topics from those chosen levels.
- The assessment level continues to control which saved classes can receive the generated Google Forms.
- Mixed-level question sets preserve each question's original `Level`, `Topic_Code` and `LO_ID` in the diagnostic blueprint.

### Comprehensive Auto Build
- Comprehensive mode has no fixed target count.
- It seeks at least two probes per represented LO when the bank has enough questions.
- It adds questions when needed to represent distinct non-empty `TLG_Key_Idea_Ref` and `Alternative_Conception_Ref` tags already present in the bank.
- It does not automatically include every Approved question.
- Coverage auditing now supports a selected scope spanning multiple curriculum levels.

### Compatibility
- No new Question Bank columns were introduced.
- No new curriculum taxonomy was introduced.
- Manual selection remains available.
- Existing V2.4.3 classes, Question Bank and Google OAuth data can be copied with `scripts/migrate_from_v243.py`.
- Gemini API keys remain session-only and are not migrated.

## Automated verification
- `python -m compileall -q app src scripts`: passed.
- `pytest -q`: **56 passed**.
- Added tests cover cumulative level eligibility, mixed-level question pools, LO-balanced Auto Build, comprehensive TLG-tag representation and V2.4.4 UI contracts.
- The packaged ZIP was extracted into a fresh directory and re-run through compileall and the full test suite: **56 passed**.

## Deliberate limits
- Auto Build can only balance against metadata that exists in the Approved Question Bank. It does not infer hidden curriculum concepts from question wording.
- Comprehensive coverage cannot manufacture questions for missing LOs or missing mappings; the UI warns when the Approved bank cannot cover an official LO in the selected topic scope.
- Teachers retain final control through Manual selection and can review the Auto Build preview before creating Forms.
