from pathlib import Path

import pandas as pd

from src.config import CONCEPT_MASTER_PATH, QUESTION_BANK_COLUMNS, TEMPLATES_DIR
from src.curriculum import load_concept_master
from src.question_bank import prepare_imported_question_bank, validate_question_bank
from src.diagnostic import eligible_questions


def test_concept_master_learning_outcome_keys_are_unique_and_topics_resolve():
    lo, _, topics = load_concept_master()
    assert not lo.empty
    assert lo["LO_ID"].is_unique
    assert lo["LO_ID"].astype(str).str.strip().ne("").all()
    assert set(lo["Topic_Code"]).issubset(set(topics["Topic_Code"]))
    assert set(lo["Level"]).issubset({"P3", "P4", "P5", "P6"})


def test_packaged_master_question_bank_has_exact_schema():
    path = Path(__file__).resolve().parents[1] / "data/question_bank/master_question_bank.csv"
    bank = pd.read_csv(path, dtype=str)
    assert list(bank.columns) == QUESTION_BANK_COLUMNS


def test_packaged_v241_system_test_questions_validate_against_real_master():
    lo, _, _ = load_concept_master()
    path = TEMPLATES_DIR / "V2_4_1_system_test_questions.csv"
    test_bank = prepare_imported_question_bank(pd.read_csv(path, dtype=str).fillna(""))
    validation = validate_question_bank(test_bank, lo)
    assert validation["Valid"].all(), validation[~validation["Valid"]].to_dict(orient="records")
    for kind in ["Topic", "Pre-WA", "EOY"]:
        pool = eligible_questions(test_bank, "P3", ["P3-DIV-LNL", "P3-INT-MAG"], kind)
        assert len(pool) == 3
