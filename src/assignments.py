from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .google_forms_api import list_form_manifests, save_form_manifest


def assignment_title(manifest: dict) -> str:
    title = str(manifest.get("title", manifest.get("diagnostic_id", "Diagnostic"))).strip()
    class_name = str(manifest.get("class_name", "")).strip()
    suffix = f" — {class_name}" if class_name else ""
    return title[:-len(suffix)] if suffix and title.endswith(suffix) else title


def list_assignments(folder: str | Path) -> list[dict]:
    rows = []
    for manifest in list_form_manifests(folder):
        if not manifest.get("diagnostic_id") or not manifest.get("class_name"):
            continue
        item = dict(manifest)
        item["assignment_title"] = assignment_title(item)
        item["links_available"] = bool(item.get("responder_uri")) and not bool(item.get("links_cleared"))
        rows.append(item)
    rows.sort(key=lambda m: str(m.get("created_at", "")), reverse=True)
    return rows


def clear_assignment_links(manifest: dict, folder: str | Path) -> dict:
    updated = dict(manifest)
    updated.pop("_path", None)
    updated["responder_uri"] = ""
    updated["edit_uri"] = ""
    updated["links_cleared"] = True
    updated["links_cleared_at"] = datetime.now().isoformat(timespec="seconds")
    save_form_manifest(updated, folder)
    return updated
