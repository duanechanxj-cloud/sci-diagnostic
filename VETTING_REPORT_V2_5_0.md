# V2.5.0 Vetting Report

## Scope implemented
- Whole-app private authentication before navigation/data loading.
- PBKDF2-SHA256 password hashing; no bundled password.
- Hosted Google OAuth refresh-token support through hosting Secrets, with local Mac token fallback.
- Optional Google Drive persistent mutable-state snapshots; hosted app blocks if persistence is explicitly enabled but cannot initialise.
- Assessment-focused 82-LO concept master (57 Core Ideas, 25 Practices, 0 Values/Ethics/Attitudes).
- TLG-strengthened 371-question Candidate bank bundled in the full release.
- Question Bank Select All / Deselect All / Delete Selected / guarded Delete All.
- Tablet-width responsive UI rules.
- Deployment page with backup, sync and guarded restore.
- Migration script from V2.4.5 that deliberately never copies the old 105-LO concept master.

## Privacy/security checks
- `.streamlit/secrets.toml` is ignored by Git.
- `private_data/` remains ignored except its README.
- Google OAuth token/client secret files remain ignored.
- Mutable class configuration is ignored from Git.
- Google Drive state snapshots exclude `private_data/google_auth/` and `data/reference/concept_master.xlsx`.
- Gemini API key remains session-only.
- Delete All requires exact `DELETE ALL` text.

## Data integrity checks
- Bundled concept master: 82 unique LO_IDs.
- Official domains: 57 Core Ideas + 25 Practices.
- Bundled Question Bank: 371 rows, 371 unique Question_IDs.
- Review status: all Candidate.
- All 371 questions validate against the bundled 82-LO concept master.
- All 82 assessment-focused LO_IDs are represented in the bank.

## Automated tests
`python -m pytest -q` → **66 passed** before packaging.

## Remaining rollout caution
V2.5.0 is appropriate for a small private pilot. The Google Drive ZIP snapshot is deliberately simple and reliable for single-user/light use, but it is not a transactional multi-user database. Before many teachers edit the bank simultaneously, move mutable state to a proper shared database/backend with per-user write coordination.
