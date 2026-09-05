from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

from .config import (
    PROJECT_ROOT,
    QUESTION_BANK_PATH,
    CLASSES_PATH,
    GOOGLE_FORMS_DIR,
    RESPONSES_DIR,
    OUTPUT_DIR,
)

DEFAULT_FOLDER_NAME = "SASJ Science Diagnostic"  # legacy fallback name only
DEFAULT_SNAPSHOT_NAME = "science_diagnostic_state.zip"


def _mutable_paths(project_root: Path = PROJECT_ROOT) -> list[Path]:
    project_root = Path(project_root)
    rels = [
        QUESTION_BANK_PATH.relative_to(PROJECT_ROOT),
        CLASSES_PATH.relative_to(PROJECT_ROOT),
        GOOGLE_FORMS_DIR.relative_to(PROJECT_ROOT),
        RESPONSES_DIR.relative_to(PROJECT_ROOT),
        OUTPUT_DIR.relative_to(PROJECT_ROOT),
    ]
    return [project_root / rel for rel in rels]


def build_state_snapshot(project_root: Path = PROJECT_ROOT) -> bytes:
    """Create a ZIP containing only mutable operational state.

    Google OAuth client secrets/tokens are deliberately excluded. In hosted mode,
    OAuth credentials belong in Streamlit secrets; in local mode they remain under
    private_data/google_auth/ and are never copied into the remote snapshot.
    """
    project_root = Path(project_root).resolve()
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in _mutable_paths(project_root):
            if path.is_file():
                archive.write(path, path.relative_to(project_root).as_posix())
            elif path.is_dir():
                for child in sorted(path.rglob("*")):
                    if child.is_file():
                        archive.write(child, child.relative_to(project_root).as_posix())
    return buffer.getvalue()


def restore_state_snapshot(data: bytes, project_root: Path = PROJECT_ROOT) -> list[str]:
    """Safely restore a mutable-state ZIP beneath the project root."""
    project_root = Path(project_root).resolve()
    mutable_roots = [p.resolve() for p in _mutable_paths(project_root)]
    restored: list[str] = []
    with zipfile.ZipFile(BytesIO(data), "r") as archive:
        for member in archive.infolist():
            rel = Path(member.filename)
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                raise ValueError(f"Unsafe path in state snapshot: {member.filename}")
            target = (project_root / rel).resolve()
            if project_root not in target.parents and target != project_root:
                raise ValueError(f"Unsafe extraction target: {member.filename}")
            allowed = False
            for root in mutable_roots:
                if root.is_file() or root.suffix:
                    allowed = allowed or target == root
                else:
                    allowed = allowed or target == root or root in target.parents
            if not allowed:
                raise ValueError(f"Unexpected path in state snapshot: {member.filename}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
            restored.append(rel.as_posix())
    return restored


def _drive_service(credentials):
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError("Google API dependencies are missing. Run pip install -r requirements.txt") from exc
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _media_upload(data: bytes, mimetype: str):
    try:
        from googleapiclient.http import MediaIoBaseUpload
    except ImportError as exc:
        raise ImportError("Google API dependencies are missing. Run pip install -r requirements.txt") from exc
    return MediaIoBaseUpload(BytesIO(data), mimetype=mimetype, resumable=False)


def ensure_drive_folder(credentials, folder_name: str, parent_id: str | None = None) -> str:
    service = _drive_service(credentials)
    safe_name = str(folder_name).replace("'", "\\'")
    parent_clause = f" and '{parent_id}' in parents" if parent_id else ""
    result = service.files().list(
        q=f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false{parent_clause}",
        fields="files(id,name,parents,modifiedTime,appProperties)",
        pageSize=100,
    ).execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    body = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "appProperties": {"scienceDiagnosticManaged": "true"},
    }
    if parent_id:
        body["parents"] = [parent_id]
    created = service.files().create(body=body, fields="id").execute()
    return created["id"]


PROJECT_ROOT_MARKER_KEY = "scienceDiagnosticProjectRoot"
PROJECT_ROOT_MARKER_VALUE = "v2.5.2"


def _escape_drive_query(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def list_drive_folders(credentials, *, limit: int = 500) -> list[dict]:
    """List folders visible to the connected Google account for Admin selection."""
    service = _drive_service(credentials)
    folders: list[dict] = []
    page_token = None
    while len(folders) < int(limit):
        result = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken,files(id,name,parents,modifiedTime,appProperties)",
            orderBy="name_natural",
            pageSize=min(1000, max(1, int(limit) - len(folders))),
            pageToken=page_token,
        ).execute()
        folders.extend(result.get("files", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return folders[: int(limit)]


def get_drive_folder(credentials, folder_id: str) -> dict:
    folder_id = str(folder_id or "").strip()
    if not folder_id:
        raise ValueError("A Google Drive folder ID is required.")
    service = _drive_service(credentials)
    item = service.files().get(
        fileId=folder_id,
        fields="id,name,mimeType,parents,modifiedTime,appProperties,webViewLink",
    ).execute()
    if item.get("mimeType") != "application/vnd.google-apps.folder":
        raise ValueError("The selected Google Drive item is not a folder.")
    return item


def extract_drive_folder_id(value: str) -> str:
    """Accept either a bare Drive folder ID or a normal Drive folder URL."""
    value = str(value or "").strip()
    if not value:
        return ""
    if "/folders/" in value:
        return value.split("/folders/", 1)[1].split("?", 1)[0].split("/", 1)[0].strip()
    return value


def get_selected_project_root(credentials) -> dict | None:
    """Return the Drive folder most recently designated by Admin as project root."""
    service = _drive_service(credentials)
    q = (
        "mimeType='application/vnd.google-apps.folder' and trashed=false and "
        f"appProperties has {{ key='{PROJECT_ROOT_MARKER_KEY}' and value='{PROJECT_ROOT_MARKER_VALUE}' }}"
    )
    result = service.files().list(
        q=q,
        fields="files(id,name,parents,modifiedTime,appProperties,webViewLink)",
        orderBy="modifiedTime desc",
        pageSize=20,
    ).execute()
    files = result.get("files", [])
    return files[0] if files else None


def select_project_root_folder(credentials, folder_id: str) -> dict:
    """Designate an existing Drive folder as Sci Diagnostic's persistent home.

    The marker is stored on the Drive folder itself, so the app can rediscover the
    chosen root after a Streamlit restart without storing a second pointer file.
    """
    service = _drive_service(credentials)
    selected = get_drive_folder(credentials, extract_drive_folder_id(folder_id))

    # Best-effort removal of the marker from previously selected roots.
    try:
        q = (
            "mimeType='application/vnd.google-apps.folder' and trashed=false and "
            f"appProperties has {{ key='{PROJECT_ROOT_MARKER_KEY}' and value='{PROJECT_ROOT_MARKER_VALUE}' }}"
        )
        previous = service.files().list(q=q, fields="files(id,appProperties)", pageSize=50).execute().get("files", [])
        for item in previous:
            if item.get("id") == selected["id"]:
                continue
            props = dict(item.get("appProperties") or {})
            props.pop(PROJECT_ROOT_MARKER_KEY, None)
            service.files().update(fileId=item["id"], body={"appProperties": props}, fields="id").execute()
    except Exception:
        # Selection must not fail just because an old marker could not be cleaned up.
        pass

    props = dict(selected.get("appProperties") or {})
    props[PROJECT_ROOT_MARKER_KEY] = PROJECT_ROOT_MARKER_VALUE
    props["scienceDiagnosticManaged"] = "true"
    updated = service.files().update(
        fileId=selected["id"],
        body={"appProperties": props},
        fields="id,name,parents,modifiedTime,appProperties,webViewLink",
    ).execute()
    ensure_project_drive_layout(credentials, root_id=selected["id"])
    return updated


def create_and_select_project_root(credentials, folder_name: str) -> dict:
    """Create a top-level Drive folder and immediately designate it as project root."""
    folder_name = str(folder_name or "").strip()
    if not folder_name:
        raise ValueError("Enter a folder name.")
    service = _drive_service(credentials)
    created = service.files().create(
        body={
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "appProperties": {"scienceDiagnosticManaged": "true"},
        },
        fields="id,name,parents,modifiedTime,appProperties,webViewLink",
    ).execute()
    return select_project_root_folder(credentials, created["id"])


def ensure_project_drive_layout(credentials, root_id: str | None = None) -> dict[str, str]:
    """Ensure the project subfolders inside the Admin-selected Drive root."""
    if not root_id:
        selected = get_selected_project_root(credentials)
        if not selected:
            raise RuntimeError(
                "No Google Drive project folder has been selected. "
                "Admin must choose one in Deployment before Forms or persistent sync can be used."
            )
        root_id = selected["id"]
    else:
        get_drive_folder(credentials, root_id)

    app_data_id = ensure_drive_folder(credentials, "App Data", parent_id=root_id)
    forms_id = ensure_drive_folder(credentials, "Google Forms", parent_id=root_id)
    return {"root_id": root_id, "app_data_id": app_data_id, "forms_id": forms_id}


def _find_snapshot_file(service, folder_id: str, snapshot_name: str):
    safe_name = _escape_drive_query(snapshot_name)
    result = service.files().list(
        q=f"name='{safe_name}' and '{folder_id}' in parents and trashed=false",
        fields="files(id,name,modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=10,
    ).execute()
    files = result.get("files", [])
    return files[0] if files else None


def download_state_from_drive(
    credentials,
    *,
    root_folder_id: str | None = None,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
) -> bytes | None:
    service = _drive_service(credentials)
    layout = ensure_project_drive_layout(credentials, root_id=root_folder_id)
    remote = _find_snapshot_file(service, layout["app_data_id"], snapshot_name)
    if not remote:
        return None
    request = service.files().get_media(fileId=remote["id"])
    return request.execute()


def upload_state_to_drive(
    credentials,
    data: bytes,
    *,
    root_folder_id: str | None = None,
    snapshot_name: str = DEFAULT_SNAPSHOT_NAME,
) -> dict:
    service = _drive_service(credentials)
    layout = ensure_project_drive_layout(credentials, root_id=root_folder_id)
    remote = _find_snapshot_file(service, layout["app_data_id"], snapshot_name)
    media = _media_upload(data, "application/zip")
    if remote:
        return service.files().update(
            fileId=remote["id"], media_body=media, fields="id,name,modifiedTime"
        ).execute()
    return service.files().create(
        body={
            "name": snapshot_name,
            "parents": [layout["app_data_id"]],
            "appProperties": {"scienceDiagnostic": "v2.5-state"},
        },
        media_body=media,
        fields="id,name,modifiedTime",
    ).execute()

