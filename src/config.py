from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"
QUESTION_BANK_DIR = DATA_DIR / "question_bank"
TEMPLATES_DIR = DATA_DIR / "templates"

PRIVATE_DATA_DIR = PROJECT_ROOT / "private_data"
RESPONSES_DIR = PRIVATE_DATA_DIR / "responses"
GOOGLE_AUTH_DIR = PRIVATE_DATA_DIR / "google_auth"
GOOGLE_FORMS_DIR = PRIVATE_DATA_DIR / "google_forms"
GOOGLE_CLIENT_SECRET_PATH = GOOGLE_AUTH_DIR / "client_secret.json"
GOOGLE_TOKEN_PATH = GOOGLE_AUTH_DIR / "token.json"

OUTPUT_DIR = PROJECT_ROOT / "output"
DIAGNOSTICS_DIR = OUTPUT_DIR / "diagnostics"
CLASS_SUMMARIES_DIR = OUTPUT_DIR / "class_summaries"
STUDENT_REPORTS_DIR = OUTPUT_DIR / "student_reports"
ANONYMISED_EXPORTS_DIR = OUTPUT_DIR / "anonymised_exports"

CONCEPT_MASTER_PATH = REFERENCE_DIR / "concept_master.xlsx"
QUESTION_BANK_PATH = QUESTION_BANK_DIR / "master_question_bank.csv"
STANDARD_BANK_TEMPLATE_PATH = TEMPLATES_DIR / "questions_standard_TLG_audited_v1.csv"
DEFAULT_CLASSES_TEMPLATE_PATH = TEMPLATES_DIR / "classes_default.csv"
BLUEPRINT_PATH = TEMPLATES_DIR / "diagnostic_blueprints.csv"
CLASSES_PATH = REFERENCE_DIR / "classes.csv"
ANALYSIS_CONFIG_PATH = CONFIG_DIR / "analysis_config.json"

QUESTION_BANK_COLUMNS = [
    "Question_ID", "Question_Version", "Level", "Topic_Code", "LO_ID",
    "Question_Text", "Option_A", "Option_B", "Option_C", "Option_D",
    "Correct_Option", "Answer_Explanation", "Probe_Type", "TLG_Key_Idea_Ref",
    "Alternative_Conception_Ref", "Diagnostic_Use", "Review_Status", "Source_Note",
    "Teacher_Notes", "Times_Used", "Last_Used", "Created_Date", "Approved_Date",
    "Approved_By",
]


def ensure_project_folders():
    for path in [
        RESPONSES_DIR, GOOGLE_AUTH_DIR, GOOGLE_FORMS_DIR, DIAGNOSTICS_DIR,
        CLASS_SUMMARIES_DIR, STUDENT_REPORTS_DIR, ANONYMISED_EXPORTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def load_analysis_config():
    with open(ANALYSIS_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
