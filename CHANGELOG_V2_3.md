# V2.3 changes

- macOS + VS Code + `.venv` is now the primary development route.
- Added Apple-inspired Streamlit UI and explicit navigation.
- Added class configuration page.
- Replaced pupil-name input with class index number for the Mac/private pilot workflow.
- One class now receives one Google Form and one QR code.
- Multiple class Forms share one Diagnostic_ID and can be fetched/analyzed together.
- Added class/index auditing, range checks and duplicate-submission flags.
- Refactored scoring summaries to retain class separation.
- Refactored parent reports to use class + index number.
- Gemini privacy boundary strips class, index number, Pupil_Key, Response_ID and timestamp.
- Removed Windows launchers from the V2.3 package to avoid confusion with the locked-down school laptop path.
