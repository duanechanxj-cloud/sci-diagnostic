#!/usr/bin/env python3
"""Print a hosted google_oauth secrets snippet from the local token.json.

Run this only on your own Mac. The output contains credentials and must be pasted
straight into your hosting platform's encrypted Secrets settings. Do not commit it.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
token_path = ROOT / "private_data" / "google_auth" / "token.json"
client_path = ROOT / "private_data" / "google_auth" / "client_secret.json"

if not token_path.exists():
    raise SystemExit("No local token.json found. Connect Google locally in the app first.")

token = json.loads(token_path.read_text(encoding="utf-8"))
client_id = token.get("client_id", "")
client_secret = token.get("client_secret", "")

# Older token files may not retain the client secret; recover it from the Desktop client JSON.
if (not client_id or not client_secret) and client_path.exists():
    client = json.loads(client_path.read_text(encoding="utf-8")).get("installed", {})
    client_id = client_id or client.get("client_id", "")
    client_secret = client_secret or client.get("client_secret", "")


scopes = set(token.get("scopes") or [])
required_drive_scope = "https://www.googleapis.com/auth/drive"
if required_drive_scope not in scopes:
    raise SystemExit(
        "This token was created before RC8 and does not include the Drive folder-selection scope. "
        "Reconnect Google in the app, then run this script again."
    )

required = {
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": token.get("refresh_token", ""),
}
missing = [k for k, v in required.items() if not str(v).strip()]
if missing:
    raise SystemExit("Missing required local OAuth values: " + ", ".join(missing))

print("# Sensitive: paste into hosting Secrets. Do NOT commit this output.\n")
print("[google_oauth]")
print(f'client_id = {json.dumps(client_id)}')
print(f'client_secret = {json.dumps(client_secret)}')
print(f'refresh_token = {json.dumps(token["refresh_token"])}')
print(f'token_uri = {json.dumps(token.get("token_uri", "https://oauth2.googleapis.com/token"))}')
