# Migrate from V2.4.4 to V2.4.5

From inside the V2.4.5 project folder:

```bash
python scripts/migrate_from_v244.py "/path/to/Science_Diagnostic_System_V2_4_4"
```

The migration copies:
- `data/reference/classes.csv`
- `data/question_bank/master_question_bank.csv`
- `private_data/google_auth/`

It does not copy a Gemini API key because report API keys are session-only and are never stored by the app.

If you keep one permanent working project folder, you can instead use the V2.4.4-to-V2.4.5 update-only ZIP. It contains code/tests/docs only and deliberately excludes `data/` and `private_data/`.
