from __future__ import annotations

from datetime import datetime
from io import BytesIO
import json
from pathlib import Path

import pandas as pd

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/drive",
]


def _imports():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "Google Forms dependencies are missing. Run: pip install -r requirements.txt"
        ) from exc
    return Request, Credentials, InstalledAppFlow, build



def validate_oauth_client_json_bytes(data: bytes) -> dict:
    """Validate a Google OAuth Desktop-app JSON before storing it locally."""
    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise ValueError("The uploaded file is not valid JSON.") from exc

    installed = payload.get("installed")
    if not isinstance(installed, dict):
        if "web" in payload:
            raise ValueError("This is a Web OAuth client. Create/download a Desktop app OAuth client instead.")
        raise ValueError("OAuth JSON is missing the 'installed' Desktop-app configuration.")

    required = ["client_id", "client_secret", "auth_uri", "token_uri"]
    missing = [key for key in required if not str(installed.get(key, "")).strip()]
    if missing:
        raise ValueError(f"OAuth Desktop client JSON is missing: {', '.join(missing)}")
    return payload



def credentials_from_secret_mapping(secret_mapping):
    """Build refreshable Google OAuth credentials from hosted secrets.

    The refresh token, client ID and client secret should be stored in the hosting
    platform's secrets manager, never in source control.
    """
    Request, Credentials, _, _ = _imports()
    required = ["client_id", "client_secret", "refresh_token"]
    missing = [key for key in required if not str(secret_mapping.get(key, "")).strip()]
    if missing:
        raise ValueError(f"Hosted Google OAuth secrets are missing: {', '.join(missing)}")
    creds = Credentials(
        token=None,
        refresh_token=str(secret_mapping["refresh_token"]),
        token_uri=str(secret_mapping.get("token_uri", "https://oauth2.googleapis.com/token")),
        client_id=str(secret_mapping["client_id"]),
        client_secret=str(secret_mapping["client_secret"]),
        scopes=SCOPES,
    )
    creds.refresh(Request())
    if not creds.has_scopes(SCOPES):
        raise ValueError(
            "The hosted Google token does not include the Drive folder-selection permission required by V2.5.2. "
            "Reconnect Google locally and regenerate the hosted OAuth secrets."
        )
    return creds if creds.valid else None

def load_google_credentials(token_path: str | Path):
    Request, Credentials, _, _ = _imports()
    token_path = Path(token_path)
    if not token_path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.has_scopes(SCOPES):
        return None
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds if creds.valid and creds.has_scopes(SCOPES) else None


def authorize_google_account(client_secret_path: str | Path, token_path: str | Path):
    _, _, InstalledAppFlow, _ = _imports()
    client_secret_path = Path(client_secret_path)
    token_path = Path(token_path)
    if not client_secret_path.exists():
        raise FileNotFoundError(
            "Google OAuth client file not found. Upload the Desktop-app client JSON first."
        )
    token_path.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def disconnect_google_account(token_path: str | Path):
    token_path = Path(token_path)
    if token_path.exists():
        token_path.unlink()
        return True
    return False


def _forms_service(credentials):
    _, _, _, build = _imports()
    return build("forms", "v1", credentials=credentials, cache_discovery=False)


def _drive_service(credentials):
    _, _, _, build = _imports()
    return build("drive", "v3", credentials=credentials, cache_discovery=False)



def move_drive_file_to_folder(file_id: str, folder_id: str, credentials) -> None:
    """Move an app-created Drive file into the requested folder."""
    if not str(folder_id or "").strip():
        return
    drive = _drive_service(credentials)
    meta = drive.files().get(fileId=file_id, fields="parents").execute()
    previous = ",".join(meta.get("parents", []))
    kwargs = {"fileId": file_id, "addParents": folder_id, "fields": "id,parents"}
    if previous:
        kwargs["removeParents"] = previous
    drive.files().update(**kwargs).execute()

def ensure_anyone_with_link_can_respond(form_id: str, credentials) -> bool:
    """Add the Google Drive published-view permission used for public responders."""
    drive = _drive_service(credentials)
    result = drive.permissions().list(
        fileId=form_id,
        fields="permissions(id,type,role,view)",
        includePermissionsForView="published",
    ).execute()

    for permission in result.get("permissions", []):
        if (
            permission.get("type") == "anyone"
            and permission.get("role") == "reader"
            and permission.get("view") == "published"
        ):
            return True

    drive.permissions().create(
        fileId=form_id,
        body={"type": "anyone", "role": "reader", "view": "published"},
        fields="id",
    ).execute()
    return True


def _create_item_request(item: dict, index: int) -> dict:
    return {"createItem": {"item": item, "location": {"index": index}}}


def create_google_diagnostic_form(
    selected_questions: pd.DataFrame,
    title: str,
    credentials,
    description: str = "",
    identity_prompt: str = "Class index number",
    identity_help: str = "Select your own class index number carefully.",
    identity_mode: str = "index_number",
    class_code: str = "",
    class_name: str = "",
    level: str = "",
    index_min: int = 1,
    index_max: int = 41,
    diagnostic_id: str = "",
    diagnostic_type: str = "",
    publish: bool = True,
    drive_folder_id: str = "",
) -> dict:
    """Create one diagnostic Form.

    V2.4.1 production convention: one class = one Form = one QR code. The class is
    stored in the local manifest, so pupils select their class index number from a dropdown.
    Marking remains local in Python; the Form is not configured as a Google Quiz.
    """
    if selected_questions.empty:
        raise ValueError("No questions were supplied for Google Form creation.")

    required = {"Question_ID", "Question_Text", "Option_A", "Option_B", "Option_C", "Option_D"}
    missing = required - set(selected_questions.columns)
    if missing:
        raise ValueError(f"Selected questions are missing columns: {sorted(missing)}")

    if identity_mode != "index_number":
        raise ValueError("V2.4.1 supports identity_mode='index_number' for classroom Forms.")
    if not str(class_code).strip() or not str(class_name).strip():
        raise ValueError("class_code and class_name are required for a V2.4.1 classroom Form.")
    if int(index_min) < 1 or int(index_max) < int(index_min):
        raise ValueError("Invalid class index-number range.")
    if not str(title).strip():
        raise ValueError("A Form title is required.")

    # Preflight the entire question set BEFORE creating anything in Google Drive.
    # This prevents an invalid row from leaving behind an orphaned/half-built Form.
    preflight_rows = selected_questions.reset_index(drop=True)
    for _, row in preflight_rows.iterrows():
        qid = str(row["Question_ID"]).strip()
        question_text = str(row["Question_Text"]).strip()
        if not qid:
            raise ValueError("Every selected question must have a Question_ID.")
        if not question_text:
            raise ValueError(f"{qid} has empty question text.")
        options = [str(row[f"Option_{letter}"]).strip() for letter in "ABCD"]
        if any(not option for option in options):
            raise ValueError(f"{qid} has one or more blank answer options.")
        if len({option.casefold() for option in options}) != 4:
            raise ValueError(
                f"{qid} has duplicate option text. "
                "Google response mapping requires four distinct option texts."
            )

    service = _forms_service(credentials)
    created = service.forms().create(
        body={"info": {"title": title, "documentTitle": title}},
        unpublished=True,
    ).execute()
    form_id = created["formId"]
    if str(drive_folder_id or "").strip():
        move_drive_file_to_folder(form_id, str(drive_folder_id).strip(), credentials)

    service.forms().batchUpdate(
        formId=form_id,
        body={
            "requests": [{
                "updateSettings": {
                    "settings": {
                        "quizSettings": {"isQuiz": False},
                        "emailCollectionType": "DO_NOT_COLLECT",
                    },
                    "updateMask": "quizSettings.isQuiz,emailCollectionType",
                }
            }]
        },
    ).execute()

    if description:
        service.forms().batchUpdate(
            formId=form_id,
            body={
                "requests": [{
                    "updateFormInfo": {
                        "info": {"description": description},
                        "updateMask": "description",
                    }
                }]
            },
        ).execute()

    index_options = [{"value": str(i)} for i in range(int(index_min), int(index_max) + 1)]
    requests = [
        _create_item_request(
            {
                "title": identity_prompt,
                "description": identity_help,
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "DROP_DOWN",
                            "options": index_options,
                            "shuffle": False,
                        },
                    }
                },
            },
            index=0,
        )
    ]

    question_ids_in_order = []
    for number, (_, row) in enumerate(selected_questions.reset_index(drop=True).iterrows(), start=1):
        options = [str(row[f"Option_{letter}"]).strip() for letter in "ABCD"]
        requests.append(
            _create_item_request(
                {
                    "title": f"{number}. {str(row['Question_Text']).strip()}",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [{"value": option} for option in options],
                                "shuffle": False,
                            },
                        }
                    },
                },
                index=number,
            )
        )
        question_ids_in_order.append(str(row["Question_ID"]).strip())

    update_result = service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()
    replies = update_result.get("replies", [])
    if len(replies) != len(requests):
        raise RuntimeError("Google Forms returned an unexpected item-creation response.")

    identity_question_ids = replies[0].get("createItem", {}).get("questionId", [])
    if not identity_question_ids:
        raise RuntimeError("Could not determine the Google question ID for the index-number field.")
    identity_question_id = identity_question_ids[0]

    google_to_internal = {}
    internal_to_google = {}
    for internal_qid, reply in zip(question_ids_in_order, replies[1:]):
        google_ids = reply.get("createItem", {}).get("questionId", [])
        if not google_ids:
            raise RuntimeError(f"Could not determine Google question ID for {internal_qid}.")
        google_qid = google_ids[0]
        google_to_internal[google_qid] = internal_qid
        internal_to_google[internal_qid] = google_qid

    anyone_with_link = False
    if publish:
        service.forms().setPublishSettings(
            formId=form_id,
            body={
                "publishSettings": {
                    "publishState": {"isPublished": True, "isAcceptingResponses": True}
                },
                "updateMask": "publishState",
            },
        ).execute()
        anyone_with_link = ensure_anyone_with_link_can_respond(form_id, credentials)

    form = service.forms().get(formId=form_id).execute()
    return {
        "form_id": form_id,
        "title": title,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "responder_uri": form.get("responderUri", ""),
        "edit_uri": f"https://docs.google.com/forms/d/{form_id}/edit",
        "published": bool(publish),
        "anyone_with_link_can_respond": bool(anyone_with_link),
        "identity_mode": identity_mode,
        "identity_question_id": identity_question_id,
        "identity_prompt": identity_prompt,
        "class_code": str(class_code).strip(),
        "class_name": str(class_name).strip(),
        "level": str(level).strip(),
        "index_min": int(index_min),
        "index_max": int(index_max),
        "diagnostic_id": str(diagnostic_id).strip(),
        "diagnostic_type": str(diagnostic_type).strip(),
        "question_map_google_to_internal": google_to_internal,
        "question_map_internal_to_google": internal_to_google,
        "question_count": len(question_ids_in_order),
    }


def save_form_manifest(manifest: dict, folder: str | Path) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{manifest['form_id']}.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_form_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_form_manifests(folder: str | Path) -> list[dict]:
    folder = Path(folder)
    if not folder.exists():
        return []
    manifests = []
    for path in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            item = load_form_manifest(path)
            item["_path"] = str(path)
            manifests.append(item)
        except Exception:
            continue
    return manifests


def _first_text_answer(answer: dict) -> str:
    values = answer.get("textAnswers", {}).get("answers", [])
    if not values:
        return ""
    return str(values[0].get("value", "")).strip()


def fetch_google_form_responses(manifest: dict, credentials) -> pd.DataFrame:
    """Return one row per submission with class metadata supplied by the manifest."""
    service = _forms_service(credentials)
    form_id = manifest["form_id"]
    page_token = None
    raw_responses = []
    while True:
        result = service.forms().responses().list(formId=form_id, pageToken=page_token).execute()
        raw_responses.extend(result.get("responses", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    mapping = manifest["question_map_google_to_internal"]
    identity_qid = manifest.get("identity_question_id") or manifest.get("name_question_id")
    if not identity_qid:
        raise ValueError("Form manifest has no identity question ID.")

    rows = []
    for response in raw_responses:
        answers = response.get("answers", {})
        index_raw = _first_text_answer(answers.get(identity_qid, {}))
        row = {
            "Response_ID": response.get("responseId", ""),
            "Timestamp": response.get("lastSubmittedTime") or response.get("createTime", ""),
            "Class_Code": manifest.get("class_code", ""),
            "Class_Name": manifest.get("class_name", ""),
            "Level": manifest.get("level", ""),
            "Index_Number": index_raw,
        }
        for google_qid, internal_qid in mapping.items():
            row[internal_qid] = _first_text_answer(answers.get(google_qid, {}))
        rows.append(row)

    columns = [
        "Response_ID", "Timestamp", "Class_Code", "Class_Name", "Level", "Index_Number",
        *mapping.values(),
    ]
    return pd.DataFrame(rows, columns=columns)


def make_qr_png(data: str) -> BytesIO:
    if not data:
        raise ValueError("A URL is required to create a QR code.")
    try:
        import qrcode
    except ImportError as exc:
        raise ImportError("qrcode is not installed. Run: pip install -r requirements.txt") from exc
    image = qrcode.make(data)
    mem = BytesIO()
    image.save(mem, format="PNG")
    mem.seek(0)
    return mem
