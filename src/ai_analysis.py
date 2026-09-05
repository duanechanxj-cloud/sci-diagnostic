from __future__ import annotations

import json
import re
from typing import List

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

AI_PROVIDERS = ("Gemini", "OpenAI", "Claude")

AI_MODEL_OPTIONS = {
    "Gemini": {
        "Gemini 3.5 Flash-Lite — fastest / lowest cost": "gemini-3.5-flash-lite",
        "Gemini 3.5 Flash — balanced": "gemini-3.5-flash",
        "Gemini 3.6 Flash — stronger general-purpose": "gemini-3.6-flash",
        "Gemini 3.7 Flash — more capable Flash": "gemini-3.7-flash",
        "Gemini 3.8 Flash — latest Flash": "gemini-3.8-flash",
    },
    "OpenAI": {
        "GPT-5.6 Luna — lowest cost": "gpt-5.6-luna",
        "GPT-5.6 Terra — balanced": "gpt-5.6-terra",
        "GPT-5.6 Sol — most capable": "gpt-5.6-sol",
    },
    "Claude": {
        "Claude Sonnet 5 — balanced": "claude-sonnet-5",
        "Claude Opus 5 — most capable": "claude-opus-5",
    },
}

DEFAULT_AI_MODELS = {
    "Gemini": "gemini-3.5-flash-lite",
    "OpenAI": "gpt-5.6-luna",
    "Claude": "claude-sonnet-5",
}

API_KEY_GUIDES = {
    "Gemini": {
        "url": "https://aistudio.google.com/app/apikey",
        "help_url": "https://ai.google.dev/gemini-api/docs/api-key",
        "steps": [
            "Open Google AI Studio and sign in with the account you want to use for API access.",
            "Open the API key page and create or copy an active Gemini API key.",
            "Paste the key into Sci Diagnostic. Do not share the key with pupils or colleagues.",
        ],
    },
    "OpenAI": {
        "url": "https://platform.openai.com/api-keys",
        "help_url": "https://platform.openai.com/docs/quickstart",
        "steps": [
            "Open the OpenAI Platform and sign in to the API account you want to use.",
            "Create a new secret API key on the API Keys page.",
            "Copy it when it is shown, then paste it into Sci Diagnostic for this session.",
        ],
    },
    "Claude": {
        "url": "https://console.anthropic.com/settings/keys",
        "help_url": "https://docs.anthropic.com/en/api/getting-started",
        "steps": [
            "Open the Anthropic Console and sign in to the API account you want to use.",
            "Go to API Keys and create a key.",
            "Copy the key and paste it into Sci Diagnostic for this session.",
        ],
    },
}


class DiagnosticReportAnalysis(BaseModel):
    response_pattern_summary: str = Field(
        description=(
            "A child-friendly, cautious summary written directly to the primary-school pupil about "
            "what the anonymous response pattern suggests. Maximum about 65 words."
        )
    )
    concepts_to_revisit: List[str] = Field(
        description=(
            "Zero to four child-friendly Science concepts from the supplied evidence that may benefit "
            "from revision. Each item should normally be under 14 words. Do not invent concepts."
        )
    )
    suggested_next_steps: List[str] = Field(
        description=(
            "Zero to three short, practical next steps written directly to the primary-school pupil. "
            "Each item should normally be under 18 words and grounded only in the supplied evidence."
        )
    )


ParentSupportAnalysis = DiagnosticReportAnalysis


def _clean(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def prepare_anonymous_question_evidence(student_scored_rows: pd.DataFrame) -> list[dict]:
    """Convert one pupil's scored rows into the only information sent to AI.

    Intentionally excluded: Response_ID, Pupil_Key, class, index number, school,
    email and timestamps.
    """
    fields = [
        "Question_ID",
        "Topic_Code",
        "LO_ID",
        "Question_Text",
        "Student_Response",
        "Correct_Option",
        "Correct",
        "Answer_Explanation",
        "Probe_Type",
        "TLG_Key_Idea_Ref",
        "Alternative_Conception_Ref",
        "Official Topic",
        "Official Learning Outcome",
        "Official Details / Sub-points",
    ]

    evidence = []
    for _, row in student_scored_rows.iterrows():
        item = {}
        for field in fields:
            if field in row.index:
                value = row[field]
                item[field] = bool(value) if field == "Correct" else _clean(value)
        evidence.append(item)
    return evidence


def build_report_analysis_prompt(evidence: list[dict]) -> str:
    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)

    return f"""
You are supporting a Singapore Primary Science teacher in preparing an AI-assisted
learning diagnostic report for ONE ANONYMOUS primary-school pupil. The three AI-written
sections will be read by the PUPIL, so write them directly to the child in clear, encouraging
Singapore Primary Science language appropriate to the pupil's level.

PRIVACY
- The pupil's response ID, class, index number, school and contact details have not been supplied.
- Do not ask for them and do not infer identity.

PURPOSE
Analyse the supplied question-by-question diagnostic evidence and write a concise,
cautious interpretation that fits comfortably inside a two-page pupil report.

ASSESSMENT CONTEXT
- This is a low-stakes diagnostic, not a Weighted Assessment.
- A wrong answer is evidence from one question, not proof that the pupil lacks the concept.
- Avoid labels such as "weak student", "poor", "mastered", "failed", "lazy", or diagnoses.
- Use cautious language such as "may benefit from revisiting" or "the responses suggest".
- Do not infer ability, effort, attitude, SEN, ADHD, family circumstances, or any personal trait.

SCIENCE GROUNDING
- Use only the Science concepts and information present in the supplied evidence.
- Do not introduce syllabus content that is not present.
- If an Alternative_Conception_Ref is supplied, you may say a response is consistent
  with that possible misconception, but never claim the pupil definitely holds it.
- Do not repeat scores, percentages, or long topic names already visible in the report tables.

LENGTH AND OUTPUT RULES
- response_pattern_summary: maximum about 70 words; preferably 2 concise sentences.
- concepts_to_revisit: 0-4 bullets; each normally under 15 words.
- suggested_next_steps: 0-3 bullets; each normally under 22 words.
- Suggested next steps must be actions the pupil can understand and do, e.g. revisit notes,
  explain an idea aloud, compare examples, make a safe observation, draw a labelled diagram,
  or try a few fresh questions on the supplied concept.
- If all supplied evidence is correct, do not invent weaknesses. concepts_to_revisit may be empty.
- Write directly to the pupil using "you" when natural.
- Use short sentences and familiar words suitable for a primary-school child.
- Use only Science terms appropriate to the stated Primary level and supplied syllabus evidence.
- Do not use secondary-school terminology, unexplained academic jargon, or teacher-only phrases.
- Prefer wording such as "You may need to revisit how..." over "You demonstrate a misconception...".
- Keep the tone warm, specific, encouraging and compact.

Return ONLY one valid JSON object with exactly these fields:
{{
  "response_pattern_summary": "string",
  "concepts_to_revisit": ["string"],
  "suggested_next_steps": ["string"]
}}
Do not wrap the JSON in Markdown fences and do not add commentary before or after it.

QUESTION-BY-QUESTION EVIDENCE
{evidence_json}
""".strip()


def build_parent_support_prompt(evidence: list[dict]) -> str:
    return build_report_analysis_prompt(evidence)


def _normalise_provider(provider: str) -> str:
    provider = str(provider or "").strip()
    for supported in AI_PROVIDERS:
        if provider.lower() == supported.lower():
            return supported
    raise ValueError(f"Unsupported AI provider: {provider or '(blank)'}")


def model_is_supported(provider: str, model: str) -> bool:
    provider = _normalise_provider(provider)
    return str(model) in set(AI_MODEL_OPTIONS[provider].values())


def _extract_json_text(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        raise RuntimeError("The AI provider returned an empty response.")

    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise RuntimeError("The AI provider did not return the required JSON object.")
    return text[start : end + 1]


def _validate_analysis_json(text: str) -> DiagnosticReportAnalysis:
    try:
        return DiagnosticReportAnalysis.model_validate_json(_extract_json_text(text))
    except ValidationError as exc:
        raise RuntimeError(
            "The AI provider returned a response that did not match the required report format."
        ) from exc


def _call_gemini(prompt: str, *, api_key: str, model: str) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ImportError(
            "google-genai is not installed. Run: pip install -r requirements.txt"
        ) from exc

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DiagnosticReportAnalysis,
        ),
    )
    return response.text or ""


def _call_openai(prompt: str, *, api_key: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "openai is not installed. Run: pip install -r requirements.txt"
        ) from exc

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=(
            "You write compact, evidence-grounded Primary Science diagnostic report guidance. "
            "Return only the JSON object requested by the user prompt."
        ),
        input=prompt,
        max_output_tokens=900,
        store=False,
    )
    return response.output_text or ""


def _call_claude(prompt: str, *, api_key: str, model: str) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise ImportError(
            "anthropic is not installed. Run: pip install -r requirements.txt"
        ) from exc

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=900,
        system=(
            "You write compact, evidence-grounded Primary Science diagnostic report guidance. "
            "Return only the JSON object requested by the user prompt."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    text_blocks = [
        block.text
        for block in message.content
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ]
    return "\n".join(text_blocks)


def analyse_student_with_ai(
    student_scored_rows: pd.DataFrame,
    *,
    provider: str,
    api_key: str,
    model: str | None = None,
) -> DiagnosticReportAnalysis:
    provider = _normalise_provider(provider)
    api_key = str(api_key or "").strip()
    if not api_key:
        raise ValueError(f"A {provider} API key is required.")

    model = str(model or DEFAULT_AI_MODELS[provider]).strip()
    if not model_is_supported(provider, model):
        raise ValueError(f"Unsupported {provider} model: {model}")

    evidence = prepare_anonymous_question_evidence(student_scored_rows)
    if not evidence:
        raise ValueError("No question evidence was supplied.")
    prompt = build_report_analysis_prompt(evidence)

    if provider == "Gemini":
        raw_text = _call_gemini(prompt, api_key=api_key, model=model)
    elif provider == "OpenAI":
        raw_text = _call_openai(prompt, api_key=api_key, model=model)
    else:
        raw_text = _call_claude(prompt, api_key=api_key, model=model)

    return _validate_analysis_json(raw_text)


class ClassLearningGap(BaseModel):
    rank: int = Field(description="1 is the highest revision priority.")
    severity: str = Field(description="Use exactly: High, Moderate, or Lower.")
    concept: str = Field(description="Concise Primary Science concept/learning gap grounded in the supplied evidence.")
    evidence: str = Field(description="Short evidence statement using the supplied class percentages/counts.")
    interpretation: str = Field(description="Cautious teacher-facing interpretation; do not diagnose pupils.")


class TeacherClassAnalysis(BaseModel):
    class_level_analysis: str = Field(
        description=(
            "Professional class-level interpretation of the anonymous diagnostic evidence. "
            "Maximum about 160 words. Identify meaningful patterns, strengths and priorities."
        )
    )
    learning_gaps: List[ClassLearningGap] = Field(
        description=(
            "Up to six learning gaps ranked from highest to lowest revision priority. "
            "Ranking must be grounded in the supplied evidence."
        )
    )
    recommended_actions: List[str] = Field(
        description=(
            "Three to six specific next actions the teacher should take, ordered sensibly. "
            "Each should be practical and linked to the supplied evidence."
        )
    )


def prepare_anonymous_class_evidence(class_scored_rows: pd.DataFrame) -> dict:
    """Build anonymous, pre-calculated class evidence for teacher-facing AI analysis.

    Identity columns are not included. Arithmetic is performed locally so the AI interprets
    evidence rather than calculating marks.
    """
    if class_scored_rows.empty:
        raise ValueError("No class question evidence was supplied.")

    frame = class_scored_rows.copy()
    frame["Correct"] = frame["Correct"].astype(bool)
    pupil_col = "Pupil_Key" if "Pupil_Key" in frame.columns else "Response_ID"
    class_size = int(frame[pupil_col].astype(str).nunique())

    # Topic-level evidence.
    topic_cols = [c for c in ["Topic_Code", "Official Topic"] if c in frame.columns]
    topic_rows = []
    if topic_cols:
        for keys, group in frame.groupby(topic_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(topic_cols, keys))
            responses = len(group)
            correct = int(group["Correct"].sum())
            row.update({
                "responses": responses,
                "correct": correct,
                "percent_correct": round(correct / responses * 100, 1) if responses else 0.0,
                "students": int(group[pupil_col].astype(str).nunique()),
            })
            topic_rows.append(row)

    # LO-level evidence. Sort weakest first before sending to AI.
    lo_cols = [c for c in ["Topic_Code", "LO_ID", "Official Topic", "Official Learning Outcome"] if c in frame.columns]
    lo_rows = []
    if lo_cols:
        for keys, group in frame.groupby(lo_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(lo_cols, keys))
            responses = len(group)
            correct = int(group["Correct"].sum())
            misconception_errors = int(group.get("Misconception_Linked_Error", pd.Series(False, index=group.index)).astype(bool).sum())
            pct = round(correct / responses * 100, 1) if responses else 0.0
            row.update({
                "responses": responses,
                "correct": correct,
                "percent_correct": pct,
                "students": int(group[pupil_col].astype(str).nunique()),
                "misconception_linked_errors": misconception_errors,
            })
            lo_rows.append(row)
        lo_rows.sort(key=lambda x: (x["percent_correct"], -x["misconception_linked_errors"], -x["responses"]))

    # Question-level patterns: useful for spotting common distractors without identity.
    question_cols = [c for c in [
        "Question_ID", "Topic_Code", "LO_ID", "Question_Text", "Correct_Option",
        "Alternative_Conception_Ref", "Official Learning Outcome",
    ] if c in frame.columns]
    question_rows = []
    if question_cols:
        for keys, group in frame.groupby(question_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(question_cols, keys))
            responses = len(group)
            correct = int(group["Correct"].sum())
            wrong = group.loc[~group["Correct"]]
            common_wrong = ""
            common_wrong_count = 0
            if not wrong.empty and "Student_Response" in wrong.columns:
                counts = wrong["Student_Response"].astype(str).value_counts()
                if len(counts):
                    common_wrong = str(counts.index[0])
                    common_wrong_count = int(counts.iloc[0])
            row.update({
                "responses": responses,
                "correct": correct,
                "percent_correct": round(correct / responses * 100, 1) if responses else 0.0,
                "incorrect": responses - correct,
                "most_common_wrong_option": common_wrong,
                "most_common_wrong_count": common_wrong_count,
            })
            question_rows.append(row)
        question_rows.sort(key=lambda x: (x["percent_correct"], -x["responses"]))

    return {
        "class_size": class_size,
        "topic_evidence": topic_rows,
        "learning_outcome_evidence": lo_rows,
        "question_response_patterns": question_rows,
    }


def build_teacher_class_analysis_prompt(evidence: dict) -> str:
    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)
    return f"""
You are supporting a Singapore Primary Science teacher. Analyse ONE ANONYMOUS class's
low-stakes diagnostic results and prepare a concise teacher-facing instructional report.

IMPORTANT METHOD
- All scores, counts and percentages have already been calculated locally by Sci Diagnostic.
- Do NOT recalculate marks. Interpret the supplied evidence.
- No pupil names, index numbers, response IDs or contact details have been supplied.
- Do not infer or diagnose ability, effort, SEN, ADHD, motivation, family circumstances, or personal traits.
- A diagnostic snapshot is evidence for planning, not proof of mastery or inability.

SCIENCE AND SYLLABUS GROUNDING
- Use only the Primary Science concepts and learning outcomes supplied in the evidence.
- Do not introduce out-of-syllabus terminology or concepts.
- Use MOE Primary Science terminology when it is present in the evidence.
- Where a misconception reference is present, describe it only as a possible response pattern.

WHAT THE TEACHER NEEDS
1. class_level_analysis
   - Explain the most meaningful overall response patterns.
   - Mention meaningful strengths briefly, but focus on what changes instruction.
   - Distinguish a broad class gap from a difficulty concentrated in a smaller group when the evidence allows.

2. learning_gaps
   - Rank up to SIX gaps by revision priority, highest first.
   - Use severity exactly as High, Moderate, or Lower.
   - Base priority on the combination of percent correct, number of pupils/responses affected,
     misconception-linked errors and repeated weak question patterns.
   - Do not call a gap "High" merely because one isolated item was answered poorly.
   - Each entry must include a concise evidence statement.

3. recommended_actions
   - Give 3-6 concrete actions the teacher should take next.
   - Prioritise actions: what to reteach whole-class, what to revisit in a small group,
     what to check with a fresh question, and what can simply be monitored.
   - Recommend teaching moves, not generic advice such as "revise more".
   - Suggestions may include concrete examples/non-examples, diagrams, demonstrations,
     manipulatives, short retrieval checks, targeted small-group reteaching, or a recheck.

STYLE
- Professional and useful to a primary-school Science teacher.
- Concise, evidence-grounded and action-oriented.
- Do not overstate certainty.

Return ONLY one valid JSON object with exactly these fields:
{{
  "class_level_analysis": "string",
  "learning_gaps": [
    {{
      "rank": 1,
      "severity": "High",
      "concept": "string",
      "evidence": "string",
      "interpretation": "string"
    }}
  ],
  "recommended_actions": ["string"]
}}

ANONYMOUS CLASS EVIDENCE
{evidence_json}
""".strip()


def _validate_teacher_analysis_json(text: str) -> TeacherClassAnalysis:
    try:
        analysis = TeacherClassAnalysis.model_validate_json(_extract_json_text(text))
    except ValidationError as exc:
        raise RuntimeError(
            "The AI provider returned a response that did not match the required teacher-report format."
        ) from exc
    # Enforce predictable ordering and allowed severity values after schema validation.
    allowed = {"High", "Moderate", "Lower"}
    gaps = sorted(analysis.learning_gaps, key=lambda g: g.rank)[:6]
    for i, gap in enumerate(gaps, start=1):
        gap.rank = i
        if gap.severity not in allowed:
            gap.severity = "Moderate"
    analysis.learning_gaps = gaps
    analysis.recommended_actions = analysis.recommended_actions[:6]
    return analysis


def analyse_class_with_ai(
    class_scored_rows: pd.DataFrame,
    *,
    provider: str,
    api_key: str,
    model: str | None = None,
) -> TeacherClassAnalysis:
    provider = _normalise_provider(provider)
    api_key = str(api_key or "").strip()
    if not api_key:
        raise ValueError(f"A {provider} API key is required.")

    model = str(model or DEFAULT_AI_MODELS[provider]).strip()
    if not model_is_supported(provider, model):
        raise ValueError(f"Unsupported {provider} model: {model}")

    evidence = prepare_anonymous_class_evidence(class_scored_rows)
    prompt = build_teacher_class_analysis_prompt(evidence)

    if provider == "Gemini":
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ImportError("google-genai is not installed. Run: pip install -r requirements.txt") from exc
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TeacherClassAnalysis,
            ),
        )
        raw_text = response.text or ""
    elif provider == "OpenAI":
        raw_text = _call_openai(prompt, api_key=api_key, model=model)
    else:
        raw_text = _call_claude(prompt, api_key=api_key, model=model)

    return _validate_teacher_analysis_json(raw_text)
