# Upgrade from V2.5.0 to V2.5.2

V2.5.2 was built directly on the V2.5.0 codebase. No question-bank conversion is required.

## Preserve operational data

If your V2.5 deployment already uses Google Drive persistence, keep the same:

- Admin chooses the project Drive folder from **Deployment** after Google is connected.
- `snapshot_name = "science_diagnostic_state.zip"`

This lets V2.5.2 restore the existing class list, Question Bank state, Form manifests, fetched responses and generated outputs.

If you use only local files, copy your current mutable data into the V2.5.2 folder before first use:

- `data/question_bank/master_question_bank.csv`
- `data/reference/classes.csv`
- `private_data/google_forms/`
- `private_data/responses/` if present
- `output/` if you need the old generated files

Do not copy OAuth tokens into Git or a public/shared folder.

## Replace the V2.5 login Secret

V2.5.0's old single-user/multi-user login layout is intentionally removed.

Run:

```bash
python scripts/hash_password.py
```

Then configure exactly:
- Teacher password hash
- Admin password hash

## No AI-key migration

There is nothing to migrate for Gemini/OpenAI/Claude API keys. V2.5.2 deliberately requires teachers to enter them per session.


## RC4 automatic data migration

After an existing V2.5 Google Drive snapshot is restored, V2.5.2 automatically:

1. restores/upgrades the audited 371-question Standard Bank when the old bank is empty, all Candidate or the older pre-audit baseline;
2. migrates legacy class files to the timeless `Level, Class_Name, Active` schema;
3. keeps extra Admin-created questions and current-format Admin class edits.

Teacher pupil counts are entered per diagnostic and are not migrated into the class master.
