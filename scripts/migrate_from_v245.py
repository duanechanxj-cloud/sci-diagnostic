#!/usr/bin/env python3
"""Copy reusable operational setup from V2.4.5 into V2.5.0.

By default the V2.5.0 bundled 371-question TLG-strengthened bank is preserved.
Use --preserve-existing-bank only when the old master bank contains teacher edits
or approval/usage history you deliberately want to keep instead.
"""
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
    print(f"Copied {label}: {source}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("v245_folder", help="Path to the existing Science Diagnostic System V2.4.5 folder")
    parser.add_argument(
        "--preserve-existing-bank",
        action="store_true",
        help="Replace V2.5.0's bundled 371-question bank with the old master bank.",
    )
    args = parser.parse_args()

    old = Path(args.v245_folder).expanduser().resolve()
    new = Path(__file__).resolve().parents[1]
    if not old.exists():
        raise SystemExit(f"V2.4.5 folder not found: {old}")

    copy_if_exists(old / "data/reference/classes.csv", new / "data/reference/classes.csv", "classes")
    if args.preserve_existing_bank:
        copy_if_exists(
            old / "data/question_bank/master_question_bank.csv",
            new / "data/question_bank/master_question_bank.csv",
            "existing question bank",
        )
    else:
        print("Kept V2.5.0 bundled 371-question TLG-strengthened Question Bank.")

    copy_if_exists(old / "private_data/google_auth", new / "private_data/google_auth", "local Google OAuth")
    copy_if_exists(old / "private_data/google_forms", new / "private_data/google_forms", "Google Form manifests")
    copy_if_exists(old / "private_data/responses", new / "private_data/responses", "fetched response CSVs")
    copy_if_exists(old / "output", new / "output", "operational outputs")

    print("Migration complete.")
    print("V2.5.0 keeps its assessment-focused 82-LO concept master; the V2.4.5 master is never copied.")
    print("Configure V2.5.0 app login separately in Streamlit secrets.")


if __name__ == "__main__":
    main()
