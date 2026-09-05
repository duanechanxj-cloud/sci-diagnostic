# Moving from V2.4.3 to V2.4.4

Keep V2.4.3 as a backup and extract V2.4.4 into a separate folder.

From inside the new V2.4.4 folder, run:

```bash
python scripts/migrate_from_v243.py "/path/to/Science_Diagnostic_System_V2_4_3"
```

This copies:
- `data/reference/classes.csv`
- `data/question_bank/master_question_bank.csv`
- `private_data/google_auth/`

Gemini API keys are not copied because they are session-only and are never stored by the app.
