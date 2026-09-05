# V2.5.2 Deployment Candidate Guide

## 1. Install and test locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
```

The release candidate should report **71 passed**.

## 2. Create the Teacher and Admin passwords

Run:

```bash
python scripts/hash_password.py
```

Choose separate passwords for Teacher and Admin. Copy the generated block into `.streamlit/secrets.toml` for local testing or the host's encrypted Secrets editor.

V2.5.2 supports exactly these two accounts:

```toml
[auth]
enabled = true

[auth.teacher]
display_name = "Teacher"
password_hash = "pbkdf2_sha256$..."

[auth.admin]
display_name = "Admin"
password_hash = "pbkdf2_sha256$..."
```

Do not put plaintext passwords into Secrets or source code.

## 3. Keep hosted Google OAuth

If your existing V2.5 hosted OAuth Secrets are already working, keep them.

For a new setup, connect the intended Google account locally through **Google Connection**, then run:

```bash
python scripts/make_hosted_google_secrets.py
```

Paste the generated `[google_oauth]` values directly into the host's encrypted Secrets editor.

## 4. Keep the existing V2.5 persistent-state location

For an upgrade from a live V2.5 deployment, keep:

```toml
[persistence]
enabled = true
backend = "google_drive"
snapshot_name = "science_diagnostic_state.zip"
```

V2.5.2 deliberately keeps the same folder/snapshot names so the existing mutable operational state can be restored rather than starting a second empty store.

## 5. AI provider keys are not deployment Secrets

Do **not** place teacher Gemini/OpenAI/Claude keys in the repository or app Secrets.

On **Reports (AI-enabled)** each teacher chooses:

1. Gemini, OpenAI or Claude;
2. a supported model;
3. their own session-only API key.

The key is cleared when they sign out and is not included in Google Drive state snapshots.

## 6. Role checks after deployment

### Teacher login
Confirm Teacher can use:
- Classes
- Curriculum
- Create Diagnostic
- Analyse Responses
- Reports (AI-enabled)
- Google Connection

Confirm Teacher cannot see or directly open:
- Question Bank
- Deployment

### Admin login
Confirm Admin can access all Teacher pages plus:
- Question Bank
- Deployment

## 7. AI smoke tests

Using non-sensitive test data, test each provider separately:

- Gemini
- OpenAI
- Claude

For each provider verify:
- the key field is masked;
- report generation succeeds with a valid key/account;
- class/index/Response_ID are not sent in the prepared evidence;
- signing out removes the session key;
- no key appears in downloaded reports or state backups.

Provider API access, quotas and billing are controlled by the provider account supplying the key.

## 8. Standard Bank verification

Before deployment, run:

```bash
python scripts/verify_v252_release.py
```

It verifies the bundled Standard Bank is still exactly the V2.5 371-question bank.

## 9. Repository safety

Before pushing, confirm none of these are present:
- `.streamlit/secrets.toml`
- `private_data/google_auth/`
- `token.json`
- `client_secret*.json`
- fetched pupil response CSVs
- generated pupil reports
- any Gemini/OpenAI/Claude API key

Review `git status` before the first deployment.


## V2.5.2 RC4 data defaults

On first deployment/startup:

- the canonical audited Standard Bank v1 contains 371 Approved questions and is immediately usable;
- an older empty/Candidate/pre-audit baseline is upgraded after Google Drive state restore;
- 2026 classes are preloaded for P3-P6 with Unity, Thanksgiving, Empathy, Wonder, Resilience and Integrity;
- class enrolment is **not** stored in the class master; teachers enter the pupil count when creating class Forms;
- Classes is Admin-only.

The class master CSV schema is:

```text
Level,Class_Name,Active
```

There is no user-maintained class code. An internal key is generated at runtime only for Forms/response separation.


## Admin-selectable Drive folder (RC8+)

After Google OAuth is connected and Google Drive persistence is enabled, sign in as Admin and open **Deployment**. Choose the existing Google Drive folder that should be Sci Diagnostic's permanent home, or create a new one there. The app stores the choice on the Drive folder itself using its folder ID; no `folder_name` Secret is required.

RC8 requests full Google Drive scope so it can access a folder you created manually. If you used RC7 or earlier, reconnect Google locally once and rerun `python scripts/make_hosted_google_secrets.py` before updating Streamlit Cloud Secrets.
