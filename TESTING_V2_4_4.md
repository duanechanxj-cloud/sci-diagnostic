# Testing V2.4.4

Run from the project root:

```bash
source .venv/bin/activate
python -m compileall -q app src scripts
python -m pytest
```

Expected automated result for the packaged V2.4.4 build:

```text
56 passed
```

High-value manual checks before a live class launch:
1. Create a P4 diagnostic and confirm P3 and P4 can both be selected under Question levels to include.
2. Create a P6 diagnostic and confirm P3-P6 topics can be mixed while only P6 classes are offered at the class-selection step.
3. Compare Auto Build and Manual selection for the same topic scope.
4. Turn on Comprehensive testing and review the Learning Outcome coverage warning/summary.
5. Create a test Google Form and verify the pupil index dropdown, questions and QR code before use.
