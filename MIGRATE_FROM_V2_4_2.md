# Moving from V2.4.2 to V2.4.3

Keep V2.4.2 as a backup and extract V2.4.3 into a separate folder.

Create/activate the new `.venv` and install requirements, then run:

```bash
python scripts/migrate_from_v242.py "/path/to/Science_Diagnostic_System_V2_4_2"
```

The migration copies:
- classes
- the master Question Bank
- Google OAuth files

It intentionally does not copy Gemini API keys because those remain session-only.
