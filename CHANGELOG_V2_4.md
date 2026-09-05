# V2.4 changes

## UI
- Switched the Streamlit application to a high-contrast dark theme.
- Increased base/secondary text legibility and contrast.
- Added safe top spacing to prevent clipped page eyebrows/headings.
- Widened the responsive desktop content area to 1440 px.
- Standardised card sizing, row stretching, tabs and control/button heights.
- Added responsive wrapping rules for narrower windows/tablets.

## Question Bank
- Added downloadable NotebookLM/Gemini template pack.
- Added exact controlled-value references and official LO/topic references.
- Added safe import defaults and automatic Question_ID assignment for blank AI-generated IDs.
- Added dropdown controls for status, diagnostic use, probe type and correct option.
- Strengthened validation for Level/Topic/LO consistency, Diagnostic_Use and duplicate option text.
- Empty editor placeholder rows are removed safely.

## Create Diagnostic
- Added detailed filter diagnostics when the eligible question pool is empty.
- Questions tagged `Any` work for Topic, Pre-WA and EOY diagnostics.
- Diagnostic IDs now use the selected diagnostic type rather than the first question's `Diagnostic_Use` tag.
- A changed scope invalidates the old selection instead of accidentally reusing it.

## Google
- OAuth upload is checked to ensure it is a Desktop-app client before saving.
- Google Form creation preflights the full question set before creating a Form.
- Duplicate/blank options therefore fail before leaving an orphan Form in Drive.

## Response processing
- Remaining responses are re-audited after exclusions.
- Duplicate/invalid entries block scoring until ambiguity is resolved.
- Same index numbers in different classes remain separated by Class_Code.

## Future teacher rollout
- Teacher-specific classes and Google authentication remain configuration/local state rather than hard-coded values.
- A migration helper copies only V2.3 classes and OAuth setup, not old question/test data.

## Testing
- 42 automated tests passed.
- `python -m compileall -q app src` passed.
- Packaged system-test CSV validated against the real Concept Master.
- System-test questions were confirmed eligible for Topic, Pre-WA and EOY.
- Diagnostic ZIP package integration check passed.
