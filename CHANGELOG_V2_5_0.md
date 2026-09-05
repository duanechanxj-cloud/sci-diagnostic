# V2.5.0 — Private Online Deployment

## Private access
- Added whole-app username/password authentication before navigation or project data is loaded.
- Passwords are stored only as PBKDF2-SHA256 hashes in Streamlit/hosting secrets.
- Added Sign out control and support for either a single-user secret or a small `auth.users` table for later departmental accounts.
- Added `scripts/hash_password.py`; no default password is bundled.

## Hosted Google access and persistence
- Added hosted Google OAuth support using client ID, client secret and refresh token stored in hosting secrets.
- Local Mac OAuth (`private_data/google_auth/token.json`) remains available as a fallback for development.
- Added an optional Google Drive persistent-state backend for hosted deployments.
- The persistent snapshot includes the Question Bank, class list, Google Form manifests, fetched response CSVs and output files.
- OAuth secrets/tokens and the static curriculum master are deliberately excluded from persistent snapshots.
- Added a Deployment page with state backup, manual sync and guarded remote restore.
- Added `scripts/make_hosted_google_secrets.py` to generate the hosted OAuth secret values from the existing local Mac connection.

## Curriculum and Question Bank
- Replaced the bundled curriculum master with the assessment-focused 82-LO version: 57 Core Ideas + 25 Practices; Values/Ethics/Attitudes LOs are excluded from diagnostic validation.
- Bundled the TLG-strengthened 371-question bank as Candidate questions.
- Added explicit Select All / Deselect All controls in Question Bank management.
- Added Delete Selected with confirmation.
- Added Delete All with an exact `DELETE ALL` confirmation phrase.
- Backup download remains immediately available before destructive actions.

## Tablet and browser use
- Added responsive rules for tablet-width displays, including wrapping control columns and safer horizontal handling for large tables/editors.
- The app remains developed on the Mac; a school laptop or tablet only needs a browser when the app is hosted.

## Retained
- Deterministic Auto Build and Manual selection.
- Comprehensive coverage using official LO + existing TLG/Alternative Conception tags.
- One class = one Google Form = one QR code.
- Class index number instead of pupil names.
- Local Python scoring and optional anonymous Gemini report interpretation.
