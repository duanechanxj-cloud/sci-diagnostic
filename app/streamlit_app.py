from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.auth import (
    ACCOUNT_LABELS,
    ACCOUNT_TYPES,
    accounts_from_auth_config,
    authenticate_account,
    is_admin_user,
)
from src.config import ensure_project_folders
from src.runtime import hydrate_persistent_state_once
from src.ui import apply_apple_style

st.set_page_config(
    page_title="Science Diagnostic",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_apple_style()

APP_VERSION = "2.5.2"


def _secret_section(name: str) -> dict:
    try:
        value = st.secrets.get(name, {})
        return dict(value) if hasattr(value, "items") else {}
    except Exception:
        return {}


def _require_login() -> None:
    auth_config = _secret_section("auth")
    if auth_config.get("enabled") is False:
        st.session_state.setdefault(
            "auth_user",
            {
                "account_type": "admin",
                "username": "local-dev",
                "display_name": "Local development",
                "role": "admin",
            },
        )
        return

    accounts = accounts_from_auth_config(auth_config)
    if set(accounts) != set(ACCOUNT_TYPES):
        st.markdown("# Science Diagnostic")
        st.error("Teacher and Admin login have not both been configured for this deployment.")
        st.markdown(
            "Run `python scripts/hash_password.py`, then copy the generated `[auth.teacher]` and "
            "`[auth.admin]` password hashes into `.streamlit/secrets.toml` locally or your hosting "
            "platform's Secrets settings."
        )
        st.stop()

    if st.session_state.get("auth_user"):
        return

    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    st.markdown("# Science Diagnostic")
    st.caption(f"Private departmental diagnostic workspace · V{APP_VERSION}")
    with st.form("private_login", clear_on_submit=False):
        account_label = st.selectbox(
            "Account",
            options=[ACCOUNT_LABELS[account] for account in ACCOUNT_TYPES],
        )
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

    if submitted:
        account_type = next(
            key for key, label in ACCOUNT_LABELS.items() if label == account_label
        )
        user = authenticate_account(account_type, password, accounts)
        if user:
            st.session_state["auth_user"] = {
                "account_type": user.account_type,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
            }
            st.rerun()
        st.error("Password is incorrect for the selected account.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


_require_login()
ensure_project_folders()
persistence_status = hydrate_persistent_state_once()
if persistence_status.enabled and (
    "needs attention" in persistence_status.message.lower()
    or "not configured" in persistence_status.message.lower()
    or "unsupported" in persistence_status.message.lower()
):
    st.error(persistence_status.message)
    st.info(
        "Fix hosted Google OAuth/persistence Secrets before using this deployment so operational "
        "data is not written only to temporary server storage."
    )
    st.stop()

user = st.session_state.get("auth_user", {})
is_admin = is_admin_user(user)
with st.sidebar:
    st.caption(
        f"Signed in as **{user.get('display_name', 'Teacher')}** · "
        f"{str(user.get('role', 'teacher')).title()}"
    )
    if persistence_status.enabled:
        if (
            "needs attention" in persistence_status.message.lower()
            or "not configured" in persistence_status.message.lower()
        ):
            st.warning(persistence_status.message)
        else:
            st.caption("Persistent storage: Google Drive")
    else:
        st.caption("Storage: local project files")
    st.caption(f"Science Diagnostic V{APP_VERSION}")
    if st.button("Sign out", use_container_width=True):
        # This also clears every session-only AI API key.
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

build_pages = [
    st.Page("pages/Curriculum.py", title="Curriculum", icon="📚"),
]
if is_admin:
    build_pages.append(st.Page("pages/Classes.py", title="Classes", icon="👥"))
    build_pages.append(st.Page("pages/Question_Bank.py", title="Question Bank", icon="📁"))
build_pages.append(st.Page("pages/Create_Diagnostic.py", title="Create Diagnostic", icon="➕"))
build_pages.append(st.Page("pages/Assignments.py", title="Assignments", icon="📌"))

settings_pages = [
    st.Page("pages/Google_Connection.py", title="Google Connection", icon="🔗"),
]
if is_admin:
    settings_pages.append(st.Page("pages/Deployment.py", title="Deployment", icon="☁️"))

pages = {
    "Overview": [
        st.Page("pages/Home.py", title="Home", icon="🏠", default=True),
    ],
    "Build": build_pages,
    "Results": [
        st.Page("pages/Analyse_Responses.py", title="Analyse Responses", icon="📊"),
        st.Page("pages/Reports_AI.py", title="Reports (AI-enabled)", icon="📄"),
    ],
    "Settings": settings_pages,
}

navigation = st.navigation(pages)
navigation.run()
