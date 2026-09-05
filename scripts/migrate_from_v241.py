#!/usr/bin/env python3
"""Copy reusable local setup from a V2.4.1 project into V2.4.2."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def copy_if_exists(source: Path, target: Path, label: str) -> None:
    if not source.exists():
        print(f"Skipped {label}: not found")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
    print(f"Copied {label}: {source.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("v241_folder", help="Path to the existing Science Diagnostic System V2.4.1 folder")
    args = parser.parse_args()

    old = Path(args.v241_folder).expanduser().resolve()
    new = Path(__file__).resolve().parents[1]
    if not old.exists():
        raise SystemExit(f"V2.4.1 folder not found: {old}")

    copy_if_exists(old / "data/reference/classes.csv", new / "data/reference/classes.csv", "classes")
    copy_if_exists(old / "data/question_bank/master_question_bank.csv", new / "data/question_bank/master_question_bank.csv", "question bank")
    copy_if_exists(old / "private_data/google_auth", new / "private_data/google_auth", "Google OAuth")
    print("Migration complete. Gemini API keys are not copied because they are session-only.")


if __name__ == "__main__":
    main()
