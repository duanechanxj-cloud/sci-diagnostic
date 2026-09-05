# Testing V2.5.2

Automated release suite:

```bash
python -m pytest -q
```

Expected result:

```text
77 passed
```

Additional release checks:

```bash
python -m compileall -q app src scripts
python scripts/verify_v252_release.py
```

V2.5.2-specific automated checks cover:
- exact Teacher/Admin account model;
- role-aware navigation and direct Admin page guards;
- session-only API-key UI contract;
- Gemini/OpenAI/Claude provider catalog and shared response schema;
- anonymised AI evidence excluding local pupil identity;
- byte-for-byte preservation of both bundled 371-question bank CSVs.

Live provider calls are not performed by the automated test suite because they require teacher-owned external API credentials. Perform the three-provider smoke test before production use.


## RC4 class/bank/LO checks

- Teacher navigation does not expose Classes.
- Classes page rejects direct Teacher access.
- 2026 default master contains 24 P3-P6 classes and no enrolment/Class_Code columns.
- Admin class CSV import ignores legacy Class_Code/enrolment columns and replaces only uploaded years.
- Teacher enters pupil count per selected class during diagnostic creation.
- Every question-selection method warns when official LOs in scope are missing.
- `questions_standard_TLG_audited_v1.csv` and the live master bank contain the same 371 Approved questions.
- Legacy Candidate and pre-audit Standard Bank states are migrated safely.

## RC5 AI reporting checks

- [ ] Pupil AI summary uses child-friendly language and addresses the pupil directly.
- [ ] Pupil report includes response pattern, concepts to revisit and suggested next steps.
- [ ] Teacher report option appears on Reports page when AI is enabled.
- [ ] Teacher report contains class-level analysis, ranked learning gaps and recommended actions.
- [ ] Class scores/percentages match local analysis; AI is not asked to calculate marks.
- [ ] No pupil name/index/response ID is present in the class AI prompt.
- [ ] Bundled question bank has 371 Approved MOE age/scope-audited questions.

### RC9 visual spacing check
- Verify Create Diagnostic controls have visible space below each input/select block.
- Verify Question set metric cards do not touch the Review coverage expander.
- Verify the Review coverage expander, Download diagnostic backup button and Choose classes section remain visually separated.
- Verify global spacing remains comfortable on desktop and tablet widths.
