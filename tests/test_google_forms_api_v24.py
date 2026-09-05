import src.google_forms_api as gapi


class _Execute:
    def __init__(self, value): self.value = value
    def execute(self): return self.value


class _Responses:
    def __init__(self, payload): self.payload = payload
    def list(self, **kwargs): return _Execute(self.payload)


class _FormsResource:
    def __init__(self, payload): self.payload = payload
    def responses(self): return _Responses(self.payload)


class _FakeFormsService:
    def __init__(self, payload): self.payload = payload
    def forms(self): return _FormsResource(self.payload)


class _Permissions:
    def __init__(self): self.created = False
    def list(self, **kwargs): return _Execute({"permissions": []})
    def create(self, **kwargs):
        self.created = True
        assert kwargs["body"] == {"type":"anyone", "role":"reader", "view":"published"}
        return _Execute({"id":"PERMISSION_1"})


class _FakeDriveService:
    def __init__(self): self.permissions_resource = _Permissions()
    def permissions(self): return self.permissions_resource


def _manifest():
    return {
        "form_id":"FORM1", "identity_question_id":"GINDEX",
        "class_code":"P3U", "class_name":"3 Unity", "level":"P3",
        "index_min":1, "index_max":41,
        "question_map_google_to_internal":{"GQ1":"P3DQ0001"},
    }


def test_fetch_responses_maps_class_index_and_question(monkeypatch):
    payload = {"responses":[{
        "responseId":"RESP-GOOGLE-123", "lastSubmittedTime":"2026-08-30T08:00:00Z",
        "answers":{
            "GINDEX":{"textAnswers":{"answers":[{"value":"17"}]}},
            "GQ1":{"textAnswers":{"answers":[{"value":"iron"}]}},
        },
    }]}
    monkeypatch.setattr(gapi, "_forms_service", lambda credentials: _FakeFormsService(payload))
    df = gapi.fetch_google_form_responses(_manifest(), credentials=object())
    assert df.loc[0, "Response_ID"] == "RESP-GOOGLE-123"
    assert df.loc[0, "Class_Name"] == "3 Unity"
    assert df.loc[0, "Index_Number"] == "17"
    assert df.loc[0, "P3DQ0001"] == "iron"


def test_empty_form_response_fetch_has_expected_columns(monkeypatch):
    monkeypatch.setattr(gapi, "_forms_service", lambda credentials: _FakeFormsService({"responses": []}))
    df = gapi.fetch_google_form_responses(_manifest(), credentials=object())
    assert list(df.columns) == [
        "Response_ID", "Timestamp", "Class_Code", "Class_Name", "Level", "Index_Number", "P3DQ0001"
    ]
    assert df.empty


def test_anyone_with_link_permission_created(monkeypatch):
    drive = _FakeDriveService()
    monkeypatch.setattr(gapi, "_drive_service", lambda credentials: drive)
    assert gapi.ensure_anyone_with_link_can_respond("FORM1", credentials=object()) is True
    assert drive.permissions_resource.created is True

import json
import pandas as pd
import pytest


def test_validate_oauth_desktop_json_accepts_installed_client():
    payload = {
        "installed": {
            "client_id": "abc.apps.googleusercontent.com",
            "client_secret": "secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    out = gapi.validate_oauth_client_json_bytes(json.dumps(payload).encode("utf-8"))
    assert out["installed"]["client_id"].startswith("abc")


def test_validate_oauth_json_rejects_web_client():
    payload = {"web": {"client_id": "abc"}}
    with pytest.raises(ValueError, match="Web OAuth client"):
        gapi.validate_oauth_client_json_bytes(json.dumps(payload).encode("utf-8"))


class _CreateFormsResource:
    def __init__(self):
        self.create_kwargs = None
        self.batch_bodies = []
        self.publish_body = None

    def create(self, **kwargs):
        self.create_kwargs = kwargs
        return _Execute({"formId": "FORM-CREATED"})

    def batchUpdate(self, **kwargs):
        body = kwargs["body"]
        self.batch_bodies.append(body)
        requests = body.get("requests", [])
        if requests and all("createItem" in req for req in requests):
            replies = []
            for i, _ in enumerate(requests):
                replies.append({"createItem": {"questionId": [f"GQ{i}"]}})
            return _Execute({"replies": replies})
        return _Execute({})

    def setPublishSettings(self, **kwargs):
        self.publish_body = kwargs["body"]
        return _Execute({})

    def get(self, **kwargs):
        return _Execute({"responderUri": "https://docs.google.com/forms/d/e/demo/viewform"})


class _CreateFormsService:
    def __init__(self):
        self.resource = _CreateFormsResource()
    def forms(self):
        return self.resource


def _selected_questions():
    return pd.DataFrame([
        {
            "Question_ID": "Q1", "Question_Text": "Which is living?",
            "Option_A": "Rock", "Option_B": "Tree", "Option_C": "Spoon", "Option_D": "Cup",
        },
        {
            "Question_ID": "Q2", "Question_Text": "Which is magnetic?",
            "Option_A": "Iron", "Option_B": "Rubber", "Option_C": "Glass", "Option_D": "Plastic",
        },
    ])


def test_create_form_builds_index_field_and_question_map(monkeypatch):
    fake = _CreateFormsService()
    monkeypatch.setattr(gapi, "_forms_service", lambda credentials: fake)
    monkeypatch.setattr(gapi, "ensure_anyone_with_link_can_respond", lambda form_id, credentials: True)

    manifest = gapi.create_google_diagnostic_form(
        _selected_questions(),
        title="Demo — 3 Unity",
        credentials=object(),
        class_code="P3U",
        class_name="3 Unity",
        level="P3",
        index_min=1,
        index_max=41,
        diagnostic_id="D1",
        diagnostic_type="Topic",
    )

    assert fake.resource.create_kwargs["unpublished"] is True
    assert manifest["identity_question_id"] == "GQ0"
    assert manifest["question_map_google_to_internal"] == {"GQ1": "Q1", "GQ2": "Q2"}
    assert manifest["class_code"] == "P3U"
    assert manifest["published"] is True
    assert manifest["anyone_with_link_can_respond"] is True
    item_request_body = fake.resource.batch_bodies[-1]
    assert len(item_request_body["requests"]) == 3
    first_item = item_request_body["requests"][0]["createItem"]["item"]
    assert first_item["title"] == "Class index number"
    assert first_item["questionItem"]["question"]["required"] is True
    choice = first_item["questionItem"]["question"]["choiceQuestion"]
    assert choice["type"] == "DROP_DOWN"
    assert choice["shuffle"] is False
    assert [o["value"] for o in choice["options"]][:3] == ["1", "2", "3"]
    assert [o["value"] for o in choice["options"]][-1] == "41"


def test_duplicate_options_fail_before_google_form_is_created(monkeypatch):
    fake = _CreateFormsService()
    monkeypatch.setattr(gapi, "_forms_service", lambda credentials: fake)
    bad = _selected_questions().iloc[[0]].copy()
    bad.loc[bad.index[0], "Option_D"] = "rock"

    with pytest.raises(ValueError, match="duplicate option text"):
        gapi.create_google_diagnostic_form(
            bad,
            title="Bad form",
            credentials=object(),
            class_code="P3U",
            class_name="3 Unity",
            level="P3",
        )
    assert fake.resource.create_kwargs is None


def test_qr_generation_returns_png_bytes():
    qr = gapi.make_qr_png("https://example.com/form")
    data = qr.getvalue()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(data) > 500
