# Moving from V2.4.1 to V2.4.2

V2.4.2 is a small Gemini model-selection update. The diagnostic data model is unchanged.

Keep V2.4.1 as a backup, extract V2.4.2 into a separate folder, create/activate the new `.venv`, and install the requirements. Then run:

```bash
python scripts/migrate_from_v241.py "/path/to/Science_Diagnostic_System_V2_4_1"
```

This copies:
- class configuration
- the master Question Bank
- Google OAuth credentials/token

It does not copy Gemini API keys because V2.4.2 continues to keep them session-only.
