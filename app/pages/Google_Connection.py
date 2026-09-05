from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import ensure_project_folders, GOOGLE_CLIENT_SECRET_PATH, GOOGLE_TOKEN_PATH
from src.google_forms_api import (
    authorize_google_account,
    disconnect_google_account,
    validate_oauth_client_json_bytes,
)
from src.runtime import get_google_credentials_runtime, hosted_google_configured
from src.ui import page_header, card

ensure_project_folders()
page_header(
    "Google Connection",
    "Use your Google account to create class Forms, choose the project Drive folder, publish QR links and retrieve responses. Hosted deployments keep OAuth secrets in the hosting platform's Secrets settings.",
)

hosted = hosted_google_configured()
creds = None
try:
    creds = get_google_credentials_runtime()
except Exception as exc:
    st.warning(f"Google connection needs attention: {type(exc).__name__}: {exc}")

if hosted:
    if creds:
        st.success("Google account connected through hosted OAuth secrets")
        card(
            "Hosted mode",
            "The app uses a refresh token stored in the hosting platform's encrypted Secrets settings. No Google OAuth token is written into the deployed project folder.",
        )
    else:
        st.error("Hosted Google OAuth secrets are present but could not be used.")
    st.info(
        "To change the Google account used by this hosted deployment, generate a fresh local token on your Mac and replace the google_oauth values in the hosting platform's Secrets settings."
    )
else:
    if creds:
        st.success("Google account connected locally")
        card(
            "Local Mac mode",
            "The local OAuth token is stored under private_data/google_auth/ and excluded from Git. It can be used to create Forms and retrieve responses on this Mac.",
        )
        if st.button("Disconnect local Google account", use_container_width=True):
            disconnect_google_account(GOOGLE_TOKEN_PATH)
            st.success("Disconnected. Refresh this page to reconnect.")
    else:
        st.subheader("One-time local Google Cloud setup")
        st.markdown(
            """
1. Create a Google Cloud project for this app.
2. Enable **Google Forms API** and **Google Drive API**.
3. Configure the OAuth consent screen.
4. Allow Google Drive access so Admin can choose the project folder.
5. Create an **OAuth Client → Desktop app**.
6. Download the Desktop client JSON and import it below.
"""
        )
        uploaded = st.file_uploader("OAuth Desktop client JSON", type=["json"])
        if uploaded is not None:
            try:
                data = uploaded.getvalue()
                validate_oauth_client_json_bytes(data)
                GOOGLE_CLIENT_SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
                GOOGLE_CLIENT_SECRET_PATH.write_bytes(data)
                st.success("Valid Desktop OAuth client saved locally.")
            except Exception as exc:
                st.error(f"OAuth client file was not saved: {exc}")

        if not GOOGLE_CLIENT_SECRET_PATH.exists():
            st.info("Import a valid OAuth Desktop client JSON to continue.")
        elif st.button("Connect Google account", type="primary", use_container_width=True):
            try:
                authorize_google_account(GOOGLE_CLIENT_SECRET_PATH, GOOGLE_TOKEN_PATH)
                st.success("Connected. You can now create classroom Forms.")
            except Exception as exc:
                st.error(f"Google authorization failed: {type(exc).__name__}: {exc}")

        st.caption(
            "For online deployment, first connect locally on your Mac, then run `python scripts/make_hosted_google_secrets.py` to create the values you paste into the hosting platform's Secrets settings."
        )

st.caption("Never commit Google client secrets, refresh tokens or token.json to GitHub.")


st.caption("If you previously connected RC7 or earlier, reconnect once in RC8 because folder selection uses a broader Google Drive scope.")
