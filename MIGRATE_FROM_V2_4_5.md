# Migrate V2.4.5 → V2.5.0

From inside the new V2.5.0 project folder:

```bash
python scripts/migrate_from_v245.py "/path/to/Science_Diagnostic_System_V2_4_5"
```

The default migration copies classes, local Google OAuth, Form manifests, fetched responses and operational outputs, while keeping V2.5.0's new **371-question TLG-strengthened Candidate bank** and **82-LO assessment-focused curriculum master**.

If your old V2.4.5 Question Bank already contains teacher edits, approvals or usage history that you deliberately want to preserve instead, run:

```bash
python scripts/migrate_from_v245.py "/path/to/Science_Diagnostic_System_V2_4_5" --preserve-existing-bank
```

The V2.4.5 concept master is never copied because V2.5.0 intentionally moves to the 82 assessment-focused LOs.

After migration, configure `.streamlit/secrets.toml` or your hosting platform's Secrets settings for the new private app login.
