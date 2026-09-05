from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from .config import OUTPUT_DIR, RESPONSES_DIR
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


def delete_assignment(
    manifest: dict,
    folder: str | Path,
    *,
    responses_dir: str | Path = RESPONSES_DIR,
    output_dir: str | Path = OUTPUT_DIR,
) -> dict[str, int]:
    """Permanently remove one assignment's local operational artifacts.

    Artifacts are keyed by the assignment's Google Form ID. This deliberately
    does not use diagnostic_id or class_name, since those can be shared by
    multiple class assignments. The Google Form itself is never contacted.
    """
    form_id = str(manifest.get("form_id", "")).strip()
    if not form_id or Path(form_id).name != form_id:
        raise ValueError("The assignment has no safe Google Form ID.")

    manifest_path = Path(manifest.get("_path", Path(folder) / f"{form_id}.json"))
    if manifest_path.exists():
        manifest_path.unlink()

    token = re.escape(form_id)
    artifact_pattern = re.compile(rf"(^|[_\-.]){token}([_\-.]|$)")
    removed = {"manifest": int(not manifest_path.exists()), "responses": 0, "artifacts": 0}

    roots = [Path(responses_dir), Path(output_dir)]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and artifact_pattern.search(path.name):
                path.unlink()
                if root == Path(responses_dir):
                    removed["responses"] += 1
                else:
                    removed["artifacts"] += 1
    return removed
