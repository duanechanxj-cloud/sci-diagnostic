#!/usr/bin/env python3
"""Copy only safe reusable local setup from a V2.3 folder into V2.4.

Intentionally NOT copied:
- Question Bank (V2.4 has stricter validation/controlled values)
- Google Form manifests
- Pupil responses
- Generated reports

Usage:
    python scripts/migrate_from_v23.py /path/to/Science_Diagnostic_System_V2_3
"""
from __future__ import annotations

from pathlib import Path
import shutil
import sys

TARGET_ROOT = Path(__file__).resolve().parents[1]


def copy_if_exists(source: Path, target: Path) -> bool:
    if not source.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/migrate_from_v23.py /path/to/Science_Diagnostic_System_V2_3")
        return 2

    source_root = Path(sys.argv[1]).expanduser().resolve()
    if not source_root.exists():
        print(f"Source folder not found: {source_root}")
        return 2

    items = [
        (source_root / "data/reference/classes.csv", TARGET_ROOT / "data/reference/classes.csv", "classes"),
        (source_root / "private_data/google_auth/client_secret.json", TARGET_ROOT / "private_data/google_auth/client_secret.json", "OAuth client"),
        (source_root / "private_data/google_auth/token.json", TARGET_ROOT / "private_data/google_auth/token.json", "Google token"),
    ]

    copied = []
    for source, target, label in items:
        if copy_if_exists(source, target):
            copied.append(label)
            print(f"Copied {label}: {source.name}")
        else:
            print(f"Skipped {label}: source file not found")

    print("\nMigration complete.")
    print("Question Bank, Forms, pupil responses and reports were NOT copied intentionally.")
    print("Use data/templates/V2_4_system_test_questions.csv for the clean V2.4 pipeline test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
