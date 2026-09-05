# Changelog V2.5.2

## Deployment-candidate changes

- Replaced flexible/multi-user authentication with exactly two shared accounts: **Teacher** and **Admin**.
- Removed the username field from login; users choose Teacher/Admin and enter that account's password.
- Fixed roles in application code so Secrets cannot accidentally elevate Teacher to Admin.
- Added role-aware navigation.
- Protected Question Bank and Deployment pages with direct Admin checks.
- Added provider-neutral AI report analysis supporting **Gemini, OpenAI and Claude**.
- Added session-only per-provider API-key fields and a clear-all control.
- Added in-app provider key guides and links.
- Preserved the existing anonymisation path before AI calls.
- Preserved the existing report schema/PDF generation and legacy `gemini_analysis` import compatibility.
- Added OpenAI and Anthropic Python SDK dependencies.
- Preserved the V2.5 Google OAuth and Google Drive persistence architecture.
- Replaced the older bundled Standard Bank with the user-supplied audited `questions_standard_TLG_audited_v1.csv`; all 371 questions ship Approved and ready to use.
- Added startup migration for empty/legacy Candidate/pre-audit Standard Bank states without deleting Admin-created extra questions.
- Removed the Classes page from Teacher navigation; it is Admin-only with a direct role guard.
- Preloaded the 2026 Science class master with 24 classes across P3-P6: Unity, Thanksgiving, Empathy, Wonder, Resilience and Integrity.
- Removed enrolment counts and visible class codes from class administration. Teachers enter pupil counts per selected class while creating a diagnostic.
- Added Admin add/edit/remove/activate class controls plus annual CSV replacement by year.
- Added a Learning Outcome coverage warning for Auto Build, Comprehensive and Manual selection; missing official LOs are listed but do not block the build.
- Added V2.5.2 regression/security tests.

## RC5 — AI reporting + MOE age/scope bank

- Pupil AI sections are now explicitly written directly to the child using age-appropriate Primary Science language.
- Pupil AI continues to fill: What the response pattern suggests; Concepts to revisit; Suggested next steps.
- Added one AI-assisted teacher report per selected class.
- Teacher report includes class-level analysis, learning gaps ranked by revision priority/severity, and recommended next course of action.
- All marks, counts and percentages are calculated locally before AI interpretation.
- Teacher AI receives anonymous aggregated class evidence only; pupil identifiers are not sent.
- Replaced the bundled Standard Bank with the 371-question MOE age/scope-audited revision; all questions remain Approved.

- Report export now produces a single combined PDF containing each class teacher report followed by all pupil reports in index-number order.


## RC7 — persistent Assignments + timeless classes
- Added a Teacher/Admin Assignments page backed by persistent Google Form manifests.
- Teachers can return later to retrieve the pupil Form link and QR code for each class assignment.
- Admin can clear saved launch links while retaining assignment history and the Google Form itself.
- Removed Year from class management. Class master is now Level, Class_Name, Active only.
- Bundled defaults remain P3-P6 × Unity, Thanksgiving, Empathy, Wonder, Resilience and Integrity.
- CSV class upload now replaces the complete current class master; no annual files are required.
- Google Drive persistence root defaults to `SASJ Science Diagnostic`.
- App-created Google Forms are moved into the `Google Forms` subfolder under that Drive root.

## RC8 — Admin-selectable Google Drive project root

- Admin can choose any accessible existing Google Drive folder as Sci Diagnostic's persistent home.
- The selected folder is remembered by Drive ID/appProperties, not by folder name.
- App Data and Google Forms subfolders are created inside the selected root.
- Google Drive OAuth scope upgraded from `drive.file` to `drive` so an existing user-created folder can be selected.
- Existing RC7-or-earlier OAuth tokens must be re-authorised once and hosted OAuth secrets regenerated.

### RC9 UI spacing refinement
- Added a global vertical-rhythm rule so Streamlit inputs, selectors, uploaders, buttons, alerts, data blocks and expanders have consistent space below them.
- Added spacing below horizontal metric/card rows so summary cards no longer touch the next expander or control.
- Increased separation around major section headings and dividers on Create Diagnostic and throughout the app.
