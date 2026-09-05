# V2.5.0 Private Online Deployment Guide

This release is designed so development stays on the Mac, while the deployed app can be opened from a normal browser on a school laptop or tablet.

## 1. Test locally first

Create/activate the project virtual environment and install requirements as usual.

Generate a private app password hash:

```bash
python scripts/hash_password.py
```

Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and paste only the generated hash. The real password itself is never stored in the project.

For local Mac testing you may set `persistence.enabled = false`.

## 2. Prepare hosted Google OAuth

V2.5.0 continues to use your existing Google Forms/Drive OAuth scopes. First connect the intended Google account locally through **Google Connection**.

Then run:

```bash
python scripts/make_hosted_google_secrets.py
```

The command prints a sensitive `[google_oauth]` block. Paste it directly into the hosting platform's encrypted Secrets editor. Do not save the output in the project or commit it to Git.

If your organisation changes the OAuth project's publishing/approval status, regenerate the hosted OAuth values when needed.

## 3. Enable persistent storage for hosted use

Add this to hosted Secrets:

```toml
[persistence]
enabled = true
backend = "google_drive"
folder_name = "Science Diagnostic V2.5 Data"
snapshot_name = "science_diagnostic_state.zip"
```

On the first authenticated startup, the app creates a Google Drive folder and initial state snapshot. On later sessions it restores that snapshot before loading the app pages.

If persistence is enabled but Google OAuth/persistence cannot initialise, V2.5.0 blocks the app rather than silently relying on temporary hosted storage.

## 4. Configure private app login

Single-user example:

```toml
[auth]
enabled = true
username = "teacher"
display_name = "Science Teacher"
role = "admin"
password_hash = "pbkdf2_sha256$..."
```

Small departmental account layout is also supported:

```toml
[auth]
enabled = true

[auth.users.teacher1]
display_name = "Teacher 1"
role = "teacher"
password_hash = "pbkdf2_sha256$..."

[auth.users.admin]
display_name = "Science Admin"
role = "admin"
password_hash = "pbkdf2_sha256$..."
```

V2.5.0 supports the account layout, but its persistent-state model is still intended for a small private pilot rather than heavy simultaneous multi-user editing.

## 5. Repository safety

Use a private repository for deployment. Before pushing, confirm that none of these are present:

- `.streamlit/secrets.toml`
- `private_data/google_auth/`
- `token.json`
- `client_secret*.json`
- fetched pupil response CSVs
- generated pupil reports

The included `.gitignore` covers these paths. Still review `git status` before every first deployment.

## 6. First hosted check

After deployment:

1. Confirm the login page appears before any app navigation.
2. Sign in.
3. Open **Deployment** and confirm Google OAuth and Persistence show the expected modes.
4. Download a state backup once.
5. Add a harmless test class or edit a Candidate question, save, then refresh/restart the hosted app and confirm the change persists.
6. Create a test Google Form before using the system with real pupils.

## 7. Tablet use

No Python installation is needed on the tablet. Open the hosted URL in the browser and sign in. V2.5.0 includes responsive layouts for tablet-width screens; large Question Bank tables remain horizontally scrollable when needed.
