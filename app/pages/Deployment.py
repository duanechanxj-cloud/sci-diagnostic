from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.auth import is_admin_user
from src.config import PROJECT_ROOT
from src.persistence import (
    build_state_snapshot,
    create_and_select_project_root,
    extract_drive_folder_id,
    get_selected_project_root,
    list_drive_folders,
    select_project_root_folder,
)
from src.runtime import (
    force_pull_runtime_state,
    get_google_credentials_runtime,
    hosted_google_configured,
    persist_runtime_state,
    persistence_config,
)
from src.ui import page_header, metric_card


user = st.session_state.get("auth_user", {})
if not is_admin_user(user):
    st.error("Admin access is required for this page.")
    st.stop()

page_header(
    "Deployment",
    "Check private-login, hosted Google access and persistent storage before using the app from a school laptop or tablet.",
)

user = st.session_state.get("auth_user", {})
config = persistence_config()

c1, c2, c3 = st.columns(3)
with c1:
    metric_card("Signed in", user.get("display_name", user.get("username", "Teacher")), user.get("role", "teacher"))
with c2:
    metric_card("Google OAuth", "Hosted" if hosted_google_configured() else "Local", "Forms + Drive access")
with c3:
    metric_card(
        "Persistence",
        "Google Drive" if config.get("enabled") else "Local only",
        "Remote state snapshot" if config.get("enabled") else "Fine for Mac development",
    )

st.subheader("Google Drive project folder")
st.caption(
    "Choose the Google Drive folder that will be Sci Diagnostic's permanent home. "
    "The app remembers the selected folder by its Drive ID, so duplicate folder names are safe."
)

if not config.get("enabled"):
    st.info("Enable Google Drive persistence in Streamlit Secrets before choosing the project folder.")
else:
    try:
        drive_creds = get_google_credentials_runtime()
    except Exception as exc:
        drive_creds = None
        st.error(f"Google credentials could not be loaded: {type(exc).__name__}: {exc}")

    if not drive_creds:
        st.warning(
            "Connect/reconnect the Google account first. V2.5.2 folder selection requires the current Google Drive permission."
        )
    else:
        try:
            current_root = get_selected_project_root(drive_creds)
        except Exception as exc:
            current_root = None
            st.error(f"Could not read the current Drive folder: {type(exc).__name__}: {exc}")

        if current_root:
            st.success(f"Current project folder: {current_root.get('name', 'Google Drive folder')}")
            st.caption(f"Drive folder ID: `{current_root.get('id', '')}`")
            if current_root.get("webViewLink"):
                st.link_button("Open current folder in Google Drive", current_root["webViewLink"], use_container_width=True)
        else:
            st.warning("No Google Drive project folder has been selected yet.")

        with st.expander("Select an existing Google Drive folder", expanded=not bool(current_root)):
            try:
                folders = list_drive_folders(drive_creds, limit=500)
            except Exception as exc:
                folders = []
                st.error(f"Could not list Drive folders: {type(exc).__name__}: {exc}")

            if folders:
                labels = {
                    f"{item.get('name', 'Unnamed folder')}  ·  {item.get('id', '')[-8:]}": item.get("id", "")
                    for item in folders
                }
                selected_label = st.selectbox("Drive folder", list(labels.keys()), key="deployment_drive_folder_pick")
                if st.button("Use selected Drive folder", type="primary", use_container_width=True):
                    try:
                        chosen = select_project_root_folder(drive_creds, labels[selected_label])
                        st.success(f"Sci Diagnostic will now use: {chosen.get('name', 'selected folder')}")
                        status = persist_runtime_state()
                        st.info(status.message)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Folder was not selected: {type(exc).__name__}: {exc}")
            else:
                st.info("No Drive folders were returned. You can paste a folder URL/ID below instead.")

            pasted = st.text_input(
                "Or paste a Google Drive folder URL / folder ID",
                key="deployment_drive_folder_url",
                placeholder="https://drive.google.com/drive/folders/...",
            )
            if st.button("Use pasted folder", use_container_width=True, disabled=not bool(pasted.strip())):
                try:
                    chosen = select_project_root_folder(drive_creds, extract_drive_folder_id(pasted))
                    st.success(f"Sci Diagnostic will now use: {chosen.get('name', 'selected folder')}")
                    status = persist_runtime_state()
                    st.info(status.message)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Folder was not selected: {type(exc).__name__}: {exc}")

        with st.expander("Create a new Drive folder instead"):
            new_name = st.text_input("New folder name", value="SASJ Science Diagnostic", key="deployment_new_drive_folder")
            if st.button("Create and use this folder", use_container_width=True):
                try:
                    chosen = create_and_select_project_root(drive_creds, new_name)
                    st.success(f"Created and selected: {chosen.get('name', new_name)}")
                    status = persist_runtime_state()
                    st.info(status.message)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Folder could not be created: {type(exc).__name__}: {exc}")

        st.caption(
            "Inside your chosen folder, Sci Diagnostic creates only the subfolders it needs: "
            "App Data (persistent state) and Google Forms (Forms generated by the app)."
        )

st.subheader("Operational state")
st.caption(
    "Persistent snapshots include the Question Bank, class list, Google Form manifests, fetched response CSVs and output files. Google OAuth secrets/tokens are deliberately excluded."
)

st.download_button(
    "Download state backup",
    build_state_snapshot(PROJECT_ROOT),
    file_name="science_diagnostic_state_backup.zip",
    mime="application/zip",
    use_container_width=True,
)

if config.get("enabled"):
    try:
        creds = get_google_credentials_runtime()
    except Exception as exc:
        creds = None
        st.error(f"Google credentials could not be loaded: {type(exc).__name__}: {exc}")

    if not creds:
        st.warning("Persistent Google Drive storage is enabled, but hosted Google OAuth is not ready.")
    else:
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Sync state to Google Drive", type="primary", use_container_width=True):
                status = persist_runtime_state()
                if "failed" in status.message.lower():
                    st.error(status.message)
                else:
                    st.success(status.message)
        with s2:
            confirm_pull = st.checkbox("I understand remote restore replaces local mutable state", key="deployment_pull_confirm")
            if st.button("Restore state from Google Drive", use_container_width=True, disabled=not confirm_pull):
                status = force_pull_runtime_state()
                if "failed" in status.message.lower() or "not configured" in status.message.lower():
                    st.error(status.message)
                else:
                    st.success(status.message)
                    st.info("Refresh the app after restoring to reload all pages from the restored state.")
else:
    st.info(
        "This deployment is using local project files. For a hosted Streamlit deployment, enable the Google Drive snapshot backend in Secrets so app data does not depend on the server's temporary filesystem."
    )

st.subheader("Hosted setup checklist")
st.markdown(
    """
- Configure private app login in **Secrets**; do not hard-code passwords.
- Configure `google_oauth` using a refresh token generated on your Mac.
- Enable the `persistence` Google Drive snapshot backend for hosted use.
- Keep `.streamlit/secrets.toml`, `private_data/`, OAuth JSON/token files and pupil-response data out of Git.
- Use the hosted URL from the school laptop or tablet; Python runs on the server, not on the device.
"""
)
