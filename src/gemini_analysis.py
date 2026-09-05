"""Backward-compatible Gemini wrapper.

V2.5.2 uses src.ai_analysis for Gemini, OpenAI and Claude. This module remains so
older tests/notebooks/imports continue to work without changing V2.5 behaviour.
"""
from __future__ import annotations

import pandas as pd

from src.ai_analysis import (
    AI_MODEL_OPTIONS,
    DEFAULT_AI_MODELS,
    DiagnosticReportAnalysis,
    ParentSupportAnalysis,
    build_parent_support_prompt,
    build_report_analysis_prompt,
    prepare_anonymous_question_evidence,
    analyse_student_with_ai,
)

DEFAULT_GEMINI_MODEL = DEFAULT_AI_MODELS["Gemini"]
GEMINI_MODEL_OPTIONS = {
    label: model_id
    for label, model_id in AI_MODEL_OPTIONS["Gemini"].items()
    if model_id in {
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
    }
}


def analyse_student_with_gemini(
    student_scored_rows: pd.DataFrame,
    api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
) -> DiagnosticReportAnalysis:
    return analyse_student_with_ai(
        student_scored_rows,
        provider="Gemini",
        api_key=api_key,
        model=model,
    )
