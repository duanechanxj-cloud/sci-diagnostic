# V2.4.5

## Question Bank workflow
- Added **Import & Review** and **Manage Question Bank** tabs.
- Added multi-file CSV upload with `accept_multiple_files=True`.
- Multiple imports are prepared as one batch while keeping app-assigned Question_IDs unique.
- Added **Approve All** for valid Candidate questions in an import batch.
- Added **Save All** to commit an imported batch at once.
- Added filtered **Approve All** in Question Bank management.
- Added **Save All** for spreadsheet-style bulk edits.
- Added search and filters for the permanent P3-P6 bank.
- Added detailed single-question inspection/editing in the management tab.
- Preserved teacher-edited local records when a re-upload contains a matching Question_ID in normal append mode.
- Approval dates are synchronised when the Question Bank is saved.

## Retained
- V2.4.4 Auto Build and cumulative lower-level topic selection.
- Comprehensive testing.
- Manual diagnostic selection.
- Google Forms/QR workflow, privacy model, local scoring and optional AI-enabled reporting.
