import pandas as pd
from .config import CONCEPT_MASTER_PATH
from .io_utils import clean_text

def load_concept_master(path=CONCEPT_MASTER_PATH):
    sheets = pd.read_excel(path, sheet_name=None)

    required = {"Learning_Outcomes", "Scope_Notes", "Topic_Index"}
    missing = required - set(sheets)
    if missing:
        raise ValueError(f"Concept Master is missing required sheets: {sorted(missing)}")

    learning_outcomes = sheets["Learning_Outcomes"].copy()
    scope_notes = sheets["Scope_Notes"].copy()
    topics = sheets["Topic_Index"].copy()

    for df in (learning_outcomes, scope_notes, topics):
        for col in df.columns:
            df[col] = df[col].map(clean_text)

    return learning_outcomes, scope_notes, topics

def get_learning_outcomes(level=None, topic_codes=None, domain=None, path=CONCEPT_MASTER_PATH):
    learning_outcomes, _, _ = load_concept_master(path)
    df = learning_outcomes.copy()

    if level:
        df = df[df["Level"].eq(level)]
    if topic_codes:
        df = df[df["Topic_Code"].isin(topic_codes)]
    if domain:
        df = df[df["Official Domain"].eq(domain)]

    return df.reset_index(drop=True)

def get_core_ideas(level=None, topic_codes=None, path=CONCEPT_MASTER_PATH):
    return get_learning_outcomes(
        level=level,
        topic_codes=topic_codes,
        domain="Core Ideas",
        path=path,
    )

def get_topic_scope_notes(topic_codes, path=CONCEPT_MASTER_PATH):
    _, scope_notes, _ = load_concept_master(path)
    if isinstance(topic_codes, str):
        topic_codes = [topic_codes]
    return scope_notes[scope_notes["Topic_Code"].isin(topic_codes)].reset_index(drop=True)

def curriculum_lookup(path=CONCEPT_MASTER_PATH):
    learning_outcomes, _, _ = load_concept_master(path)
    return learning_outcomes.set_index("LO_ID").to_dict(orient="index")
