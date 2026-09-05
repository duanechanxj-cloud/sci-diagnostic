from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .config import GOOGLE_TOKEN_PATH, PROJECT_ROOT
from .google_forms_api import credentials_from_secret_mapping, load_google_credentials
from .question_bank import ensure_standard_bank_v1
from .classes import ensure_default_classes
from .persistence import (
    DEFAULT_SNAPSHOT_NAME,
    build_state_snapshot,
    download_state_from_drive,
    restore_state_snapshot,
    upload_state_to_drive,
)


@dataclass(frozen=True)
class PersistenceStatus:
    enabled: bool
    backend: str
    message: str


def _secrets_dict() -> dict[str, Any]:
    try:
        import streamlit as st
        return dict(st.secrets)
    except Exception:
        return {}


def _ensure_runtime_baselines():
    bank_changed, bank_message = ensure_standard_bank_v1()
    classes_changed, classes_message = ensure_default_classes()
    changed = bank_changed or classes_changed
    messages = []
    if bank_changed:
        messages.append(bank_message)
    if classes_changed:
        messages.append(classes_message)
    return changed, " ".join(messages)


def get_google_credentials_runtime():
    """Use hosted OAuth refresh-token secrets when configured; otherwise local token.json."""
    secrets = _secrets_dict()
    hosted = secrets.get("google_oauth")
    if isinstance(hosted, Mapping) and hosted.get("refresh_token"):
        return credentials_from_secret_mapping(hosted)
    return load_google_credentials(GOOGLE_TOKEN_PATH)


def hosted_google_configured() -> bool:
    secrets = _secrets_dict()
    hosted = secrets.get("google_oauth")
    return isinstance(hosted, Mapping) and bool(hosted.get("refresh_token"))


def persistence_config() -> dict[str, Any]:
    secrets = _secrets_dict()
    raw = secrets.get("persistence")
    if not isinstance(raw, Mapping):
        return {"enabled": False, "backend": "local"}
    config = dict(raw)
    config.setdefault("enabled", False)
    config.setdefault("backend", "google_drive")
    config.setdefault("snapshot_name", DEFAULT_SNAPSHOT_NAME)
    return config


def hydrate_persistent_state_once() -> PersistenceStatus:
    """Restore hosted state once per Streamlit session, before page data is loaded."""
    try:
        import streamlit as st
    except Exception:
        return PersistenceStatus(False, "local", "Streamlit runtime unavailable.")

    config = persistence_config()
    if not bool(config.get("enabled")):
        changed, baseline_message = _ensure_runtime_baselines()
        message = "Local storage mode."
        if changed:
            message += " " + baseline_message
        return PersistenceStatus(False, "local", message)
    if str(config.get("backend")) != "google_drive":
        return PersistenceStatus(True, str(config.get("backend")), "Unsupported persistence backend.")

    if st.session_state.get("v250_state_hydrated"):
        return PersistenceStatus(True, "google_drive", st.session_state.get("v250_persistence_message", "Persistent state ready."))

    creds = get_google_credentials_runtime()
    if not creds:
        message = "Persistence is enabled but Google OAuth credentials are not configured."
        st.session_state["v250_persistence_message"] = message
        return PersistenceStatus(True, "google_drive", message)

    try:
        remote = download_state_from_drive(
            creds,
            snapshot_name=str(config.get("snapshot_name")),
        )
        if remote:
            restore_state_snapshot(remote, PROJECT_ROOT)
            baseline_changed, baseline_message = _ensure_runtime_baselines()
            if baseline_changed:
                upload_state_to_drive(
                    creds,
                    build_state_snapshot(PROJECT_ROOT),
                            snapshot_name=str(config.get("snapshot_name")),
                )
                message = "Persistent Google Drive state restored and upgraded. " + baseline_message
            else:
                message = "Persistent Google Drive state restored."
        else:
            _ensure_runtime_baselines()
            upload_state_to_drive(
                creds,
                build_state_snapshot(PROJECT_ROOT),
                    snapshot_name=str(config.get("snapshot_name")),
            )
            message = "Persistent Google Drive state initialised from this deployment."
        st.session_state["v250_state_hydrated"] = True
        st.session_state["v250_persistence_message"] = message
        return PersistenceStatus(True, "google_drive", message)
    except Exception as exc:
        message = f"Persistent storage needs attention: {type(exc).__name__}: {exc}"
        st.session_state["v250_persistence_message"] = message
        return PersistenceStatus(True, "google_drive", message)


def persist_runtime_state() -> PersistenceStatus:
    config = persistence_config()
    if not bool(config.get("enabled")):
        status = PersistenceStatus(False, "local", "Saved locally.")
    else:
        creds = get_google_credentials_runtime()
        if not creds:
            status = PersistenceStatus(True, "google_drive", "Saved locally, but Google Drive persistence is not configured.")
        else:
            try:
                upload_state_to_drive(
                    creds,
                    build_state_snapshot(PROJECT_ROOT),
                            snapshot_name=str(config.get("snapshot_name")),
                )
                status = PersistenceStatus(True, "google_drive", "Saved locally and synced to persistent Google Drive storage.")
            except Exception as exc:
                status = PersistenceStatus(True, "google_drive", f"Local save succeeded but remote sync failed: {type(exc).__name__}: {exc}")

    try:
        import streamlit as st
        st.session_state["v250_persistence_message"] = status.message
    except Exception:
        pass
    return status


def force_pull_runtime_state() -> PersistenceStatus:
    config = persistence_config()
    if not bool(config.get("enabled")):
        return PersistenceStatus(False, "local", "Persistence is disabled.")
    creds = get_google_credentials_runtime()
    if not creds:
        return PersistenceStatus(True, "google_drive", "Google OAuth credentials are not configured.")
    try:
        remote = download_state_from_drive(
            creds,
            snapshot_name=str(config.get("snapshot_name")),
        )
        if not remote:
            return PersistenceStatus(True, "google_drive", "No remote snapshot exists yet.")
        restored = restore_state_snapshot(remote, PROJECT_ROOT)
        baseline_changed, baseline_message = _ensure_runtime_baselines()
        if baseline_changed:
            upload_state_to_drive(
                creds,
                build_state_snapshot(PROJECT_ROOT),
                    snapshot_name=str(config.get("snapshot_name")),
            )
            return PersistenceStatus(
                True,
                "google_drive",
                f"Restored {len(restored)} file(s) from Google Drive and upgraded V2.5 state. {baseline_message}",
            )
        return PersistenceStatus(True, "google_drive", f"Restored {len(restored)} file(s) from Google Drive.")
    except Exception as exc:
        return PersistenceStatus(True, "google_drive", f"Restore failed: {type(exc).__name__}: {exc}")
