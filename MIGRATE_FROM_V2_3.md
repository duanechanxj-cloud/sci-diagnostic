# Moving from V2.3 to V2.4

Keep V2.3 as a backup and extract V2.4 into a separate folder.

V2.4 uses the same class/index identity architecture and Google OAuth scopes, but its Question Bank validation is stricter. For that reason, do not blindly copy the V2.3 Question Bank.

## Recommended migration

From inside the V2.4 folder:

```bash
python scripts/migrate_from_v23.py /full/path/to/Science_Diagnostic_System_V2_3
```

The helper copies only:

- `data/reference/classes.csv`
- `private_data/google_auth/client_secret.json`
- `private_data/google_auth/token.json`

It intentionally does not copy:

- the old Question Bank;
- Google Form manifests;
- pupil responses;
- generated reports.

For the clean V2.4 retest, import `data/templates/V2_4_system_test_questions.csv`.
