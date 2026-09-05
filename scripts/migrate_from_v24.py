#!/usr/bin/env python3
"""Copy reusable local setup from a V2.4 project into V2.4.1.

Copies:
- class configuration
- Google OAuth client/token
- Question Bank

Does not copy response snapshots, generated reports, or old output artifacts.
"""
from pathlib import Path
import shutil
import sys

TARGET_ROOT = Path(__file__).resolve().parents[1]


def copy_if_exists(source: Path, target: Path, label: str):
    if not source.exists():
        print(f"Skipped {label}: not found")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print(f"Copied {label}: {target.name}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/migrate_from_v24.py /path/to/Science_Diagnostic_System_V2_4")
        raise SystemExit(2)
    source_root = Path(sys.argv[1]).expanduser().resolve()
    if not source_root.exists():
        print(f"Source folder not found: {source_root}")
        raise SystemExit(1)

    copy_if_exists(source_root / "data/reference/classes.csv", TARGET_ROOT / "data/reference/classes.csv", "classes")
    copy_if_exists(source_root / "private_data/google_auth/client_secret.json", TARGET_ROOT / "private_data/google_auth/client_secret.json", "OAuth client")
    copy_if_exists(source_root / "private_data/google_auth/token.json", TARGET_ROOT / "private_data/google_auth/token.json", "Google token")
    copy_if_exists(source_root / "data/question_bank/master_question_bank.csv", TARGET_ROOT / "data/question_bank/master_question_bank.csv", "Question Bank")
    print("Migration complete. Response snapshots and generated reports were intentionally not copied.")


if __name__ == "__main__":
    main()
