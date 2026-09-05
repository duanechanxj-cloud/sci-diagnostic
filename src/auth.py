from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Any, Mapping

PBKDF2_ITERATIONS = 310_000
HASH_SCHEME = "pbkdf2_sha256"
ACCOUNT_TYPES = ("teacher", "admin")
ACCOUNT_LABELS = {"teacher": "Teacher", "admin": "Admin"}


@dataclass(frozen=True)
class AuthUser:
    account_type: str
    display_name: str
    role: str

    @property
    def username(self) -> str:
        """Compatibility property for older UI code."""
        return self.account_type


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> str:
    """Create a portable PBKDF2-SHA256 password hash for Streamlit secrets."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must not be blank.")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return "$".join(
        [
            HASH_SCHEME,
            str(int(iterations)),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password against a hash produced by :func:`hash_password`."""
    try:
        scheme, iterations, salt_b64, digest_b64 = str(encoded_hash).split("$", 3)
        if scheme != HASH_SCHEME:
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", str(password).encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def accounts_from_auth_config(
    auth_config: Mapping[str, Any] | None,
) -> dict[str, dict[str, str]]:
    """Load the only two supported accounts: Teacher and Admin.

    Expected Streamlit Secrets layout::

        [auth]
        enabled = true

        [auth.teacher]
        password_hash = "..."

        [auth.admin]
        password_hash = "..."

    Display names are optional. Roles are fixed by the app and cannot be changed
    through Secrets, which prevents accidental privilege escalation.
    """
    auth_config = dict(auth_config or {})
    accounts: dict[str, dict[str, str]] = {}

    for account_type in ACCOUNT_TYPES:
        payload = auth_config.get(account_type)
        if not isinstance(payload, Mapping):
            continue
        password_hash = str(payload.get("password_hash", "")).strip()
        if not password_hash:
            continue
        accounts[account_type] = {
            "display_name": str(
                payload.get("display_name", ACCOUNT_LABELS[account_type])
            ).strip()
            or ACCOUNT_LABELS[account_type],
            "password_hash": password_hash,
            "role": account_type,
        }

    return accounts


def auth_config_is_complete(auth_config: Mapping[str, Any] | None) -> bool:
    """Return True only when both required shared accounts are configured."""
    return set(accounts_from_auth_config(auth_config)) == set(ACCOUNT_TYPES)


def authenticate_account(
    account_type: str,
    password: str,
    accounts: Mapping[str, Mapping[str, str]],
) -> AuthUser | None:
    """Authenticate one of the two fixed shared accounts."""
    account_type = str(account_type).strip().lower()
    if account_type not in ACCOUNT_TYPES:
        hashlib.sha256(str(password).encode("utf-8")).digest()
        return None

    record = accounts.get(account_type)
    if not record:
        hashlib.sha256(str(password).encode("utf-8")).digest()
        return None

    if not verify_password(password, str(record.get("password_hash", ""))):
        return None

    return AuthUser(
        account_type=account_type,
        display_name=str(record.get("display_name", ACCOUNT_LABELS[account_type]))
        or ACCOUNT_LABELS[account_type],
        role=account_type,
    )


def is_admin_user(user: Mapping[str, Any] | None) -> bool:
    return str((user or {}).get("role", "")).strip().lower() == "admin"


def is_teacher_user(user: Mapping[str, Any] | None) -> bool:
    return str((user or {}).get("role", "")).strip().lower() == "teacher"
