#!/usr/bin/env python3
from getpass import getpass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.auth import hash_password


def _ask_twice(label: str) -> str:
    password = getpass(f"{label} password: ")
    confirm = getpass(f"Confirm {label} password: ")
    if password != confirm:
        raise SystemExit(f"{label} passwords do not match.")
    if len(password) < 8:
        raise SystemExit(f"{label} password must be at least 8 characters.")
    return password


def main():
    print("Science Diagnostic V2.5.2 shared-account password generator")
    print("This creates exactly two logins: Teacher and Admin.\n")
    teacher_password = _ask_twice("Teacher")
    admin_password = _ask_twice("Admin")

    print("\nCopy this block into your Streamlit Secrets:\n")
    print("[auth]")
    print("enabled = true\n")
    print("[auth.teacher]")
    print('display_name = "Teacher"')
    print(f'password_hash = "{hash_password(teacher_password)}"\n')
    print("[auth.admin]")
    print('display_name = "Admin"')
    print(f'password_hash = "{hash_password(admin_password)}"')


if __name__ == "__main__":
    main()
