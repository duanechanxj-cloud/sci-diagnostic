from pathlib import Path
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import GOOGLE_FORMS_DIR, CLASSES_PATH
from src.question_bank import load_question_bank
from src.classes import load_classes
from src.google_forms_api import list_form_manifests
from src.ui import page_header, metric_card, workflow_grid
from src.runtime import get_google_credentials_runtime, persistence_config

page_header(
    "Science Diagnostic",
    "Build a diagnostic, launch one QR code per class, and turn responses into concept-level evidence for revision.",
    eyebrow="Primary Science",
)

bank = load_question_bank()
classes = load_classes(CLASSES_PATH)
manifests = list_form_manifests(GOOGLE_FORMS_DIR)
approved = int(bank["Review_Status"].eq("Approved").sum()) if not bank.empty else 0
active_classes = int(classes["Active"].sum()) if not classes.empty else 0
campaigns = len({m.get("diagnostic_id") for m in manifests if m.get("diagnostic_id")})

c1, c2, c3, c4 = st.columns(4)
with c1: metric_card("Approved questions", approved, "Ready for diagnostic selection")
with c2: metric_card("Active classes", active_classes, "Each class receives its own Form")
with c3: metric_card("Diagnostics created", campaigns, "Grouped across class-specific Forms")
try:
    google_connected = bool(get_google_credentials_runtime())
except Exception:
    google_connected = False
with c4: metric_card("Google", "Connected" if google_connected else "Not connected", "Forms and Drive access")

st.write("")
st.subheader("Your workflow")
workflow_grid([
    ("1. Build the diagnostic", "Choose level, scope and approved questions. The same question set can be launched to several classes."),
    ("3. Fetch and analyse", "At home, retrieve every class Form in the diagnostic and let Python score and separate the responses automatically."),
    ("2. Launch class Forms", "Streamlit creates one Google Form and one QR code for each selected class. Pupils select only their class index number."),
    ("4. Act on the evidence", "Review class concept priorities, pupil-level evidence, revision groups and optional AI-assisted report guidance using Gemini, OpenAI or Claude."),
])

storage = persistence_config()
if storage.get("enabled"):
    st.success("V2.5.2 private online mode is enabled: login protects the app and mutable operational state can persist to Google Drive.")
else:
    st.info("V2.5.2 is running in local-storage mode. This is suitable for Mac development; enable persistent storage before relying on a hosted deployment.")
