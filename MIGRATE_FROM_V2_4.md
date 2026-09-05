# Moving from V2.4 to V2.4.1

Keep V2.4 as a backup and extract V2.4.1 into a separate folder.

After creating/activating the V2.4.1 `.venv` and installing requirements, run:

```bash
python scripts/migrate_from_v24.py /path/to/Science_Diagnostic_System_V2_4
```

The migration helper copies:

- `data/reference/classes.csv`;
- `private_data/google_auth/client_secret.json`;
- `private_data/google_auth/token.json`;
- `data/question_bank/master_question_bank.csv`.

It deliberately does not copy pupil response snapshots, generated reports or output artifacts.
