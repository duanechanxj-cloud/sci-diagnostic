# Privacy - V2.5.2 private deployment candidate

V2.4.1 intentionally avoids pupil names and roster uploads.

The Google Form collects a class index number selected from a dropdown plus diagnostic answers. The class is determined by the class-specific Form/QR used.

Operational data is stored under `private_data/` and excluded from Git.

Before any supported AI provider is called, local identifiers are removed. Gemini, OpenAI and Claude do not receive class name/code, index number, Pupil_Key, Google Response_ID or timestamp.

Teacher-supplied Gemini, OpenAI and Claude API keys are session-only. The app does not write them to disk, Streamlit Secrets, Google Drive snapshots, report files, exports or logs. Signing out clears the session state.

Even without names, class + index number can identify a pupil when combined with a class list. Treat operational files as pupil data and follow the applicable school/organisation policy.
