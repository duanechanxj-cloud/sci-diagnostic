# private_data

This folder contains operational files that must not be committed to Git.

V2.4.1 uses subfolders for:

- `google_auth/` — OAuth client/token files.
- `google_forms/` — local Form manifests containing class/Form mappings.
- `responses/` — fetched class/index-number diagnostic responses.

Although V2.4.1 does not collect pupil names, class + index number can still identify a pupil when combined with a class list. Treat these files as pupil data.
