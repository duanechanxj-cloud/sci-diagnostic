# Primary Science Diagnostic System V2.5.2

V2.5.2 is the **deployment-candidate upgrade of V2.5.0**. It preserves the existing diagnostic workflow, Google Forms integration, hosted persistence, reporting, privacy model, 82 assessable Learning Outcomes and the audited 371-question Standard Bank v1 supplied for deployment.

## What changed from V2.5.0

### Exactly two shared accounts
The hosted app now has only:

- **Teacher** — normal teaching workflow.
- **Admin** — Teacher permissions plus Question Bank management and Deployment controls.

There is no user database, no account-creation screen and no arbitrary per-teacher accounts.

Teacher can access:
- Home
- Curriculum
- Create Diagnostic
- Analyse Responses
- Reports (AI-enabled)
- Google Connection

Admin can access all of the above plus:
- Classes
- Question Bank
- Deployment

Classes, Question Bank and Deployment are hidden from Teacher navigation **and** protected by direct role checks.

### Gemini + OpenAI + Claude report interpretation
The optional AI report interpretation can now use:

- Gemini
- OpenAI
- Claude

Each teacher chooses a provider and model on the **Reports (AI-enabled)** page, then supplies their own API key.

API keys are **session-only**:
- held only in Streamlit session state;
- never written to project files;
- never written to Google Drive state snapshots;
- never written into reports, exports or logs by the app;
- cleared when the user signs out;
- removable at any time with **Forget all session API keys**.

The app contains an in-app key guide with links for each provider.

### Audited Standard Bank v1 is the permanent bundled default
The user-supplied audited question bank is now the canonical bank for this and future versions:

- `data/question_bank/master_question_bank.csv`
- `data/templates/questions_standard_TLG_audited_v1.csv`

Both contain **371 unique questions**, all already marked **Approved** and immediately available in Create Diagnostic. Startup migration also repairs an empty/legacy Candidate bank and upgrades the older pre-audit 371-question baseline while preserving usage counts, Teacher Notes and extra Admin-created questions.

### Class setup simplified
- Teachers do **not** have a Classes tab.
- The 2026 class master is preloaded with P3-P6 and Unity, Thanksgiving, Empathy, Wonder, Resilience and Integrity (24 classes total).
- Admin can add, edit, remove, activate/deactivate classes and mass-update a school year by CSV.
- The class master stores no enrolment count and no visible class code.
- Teachers choose one or more classes while creating a diagnostic and enter the pupil count for each selected class.
- The app generates a hidden internal key from Level + Class Name for Google Forms/response matching; teachers never manage this key.

### Learning Outcome coverage warning
Every question-selection method now checks the selected set against the official LOs for the chosen topic scope. Missing LOs are listed before Build Diagnostic. The warning does not block the teacher, because a short diagnostic may intentionally sample only part of a topic.

## Password setup

Generate the two shared account password hashes locally:

```bash
python scripts/hash_password.py
```

The script prints a Secrets block for:

```toml
[auth.teacher]
password_hash = "..."

[auth.admin]
password_hash = "..."
```

Passwords themselves are never stored in source code.

For deliberate local development without login you may set:

```toml
[auth]
enabled = false
```

Do **not** disable authentication on the hosted deployment.

## Hosted Google OAuth and persistence

V2.5.2 preserves V2.5.0's Google Forms/Drive OAuth and Google Drive state-snapshot system.

The persistence names intentionally remain:

```toml
[persistence]
enabled = true
backend = "google_drive"
snapshot_name = "science_diagnostic_state.zip"
```

Keeping these names allows an existing V2.5 hosted state snapshot to continue into V2.5.2.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
python -m streamlit run app/streamlit_app.py
```

Expected release-test result: **77 passed**.

## Privacy model

- Pupil names are not required.
- One class receives one Form and one QR code.
- Pupils select only their class index number.
- Python performs scoring locally/server-side.
- Before any AI request, class, index number, Pupil_Key, Response_ID and timestamp are stripped.
- Teacher-supplied AI API keys are session-only.
- Login hashes, hosted OAuth values and refresh tokens belong in Streamlit/hosting Secrets, never Git.

## Deployment

Use `DEPLOYMENT_V2_5_2.md` for the deployment checklist and `MIGRATE_FROM_V2_5.md` when replacing an existing V2.5 deployment.


## Google Drive project folder

In RC8+, Admin chooses the Drive folder that will be Sci Diagnostic's permanent home from **Deployment**. You may select an existing folder or let the app create one. The app remembers the folder by its Google Drive ID/app property, not by its name. Inside it, Sci Diagnostic creates:

- `App Data/` — persistent state snapshot
- `Google Forms/` — Forms generated by Sci Diagnostic

Because Admin can select an existing user-created Drive folder, RC8 uses the Google Drive `drive` OAuth scope. Reconnect Google once after upgrading from RC7 or earlier.
