def build_question_generation_prompt(
    selected_los,
    scope_notes,
    candidates_per_lo=5,
    diagnostic_use="Topic",
):
    blocks = []

    for _, row in selected_los.iterrows():
        topic_code = row["Topic_Code"]
        notes = scope_notes[scope_notes["Topic_Code"].eq(topic_code)]
        note_lines = [
            f"- {text}"
            for text in notes["Official Note / Scope Boundary"].tolist()
            if str(text).strip()
        ]

        blocks.append(
            "\n".join([
                f"LO_ID: {row['LO_ID']}",
                f"Level: {row['Level']}",
                f"Theme: {row['Theme']}",
                f"Official Topic: {row['Official Topic']}",
                f"Official Learning Outcome: {row['Official Learning Outcome']}",
                f"Official Details / Sub-points: {row['Official Details / Sub-points']}",
                "Official scope notes:",
                *(note_lines or ["- None supplied for this topic."]),
            ])
        )

    curriculum_targets = "\n\n".join(blocks)

    return f"""You are generating candidate diagnostic MCQs for Singapore MOE Primary Science.

PURPOSE
This is a low-stakes {diagnostic_use} diagnostic for identifying conceptual learning gaps and planning targeted revision. It is not a Weighted Assessment.

SOURCE GROUNDING
1. Use only the MOE Primary Science Syllabus and relevant TLG source files provided to you.
2. Stay strictly inside the stated level and scope boundaries.
3. Do not introduce content, terminology or processes outside the supplied sources.
4. Questions must map to the supplied LO_ID.
5. TLG Alternative Conceptions may inform distractors only when explicitly supported by the source.

QUESTION DESIGN
- Plain-text MCQ only.
- Four options: A, B, C, D.
- One unambiguously correct answer.
- Low reading load.
- One Science idea per item.
- Basic conceptual understanding is the target.
- Avoid trick questions, double negatives and unnecessary story contexts.
- No diagrams, pictures, graphs or tables.
- Produce {candidates_per_lo} genuinely different candidate questions per LO_ID.

CURRICULUM TARGETS
{curriculum_targets}

OUTPUT
Return only CSV inside one code block with this exact header:

Level,Topic_Code,LO_ID,Question_Text,Option_A,Option_B,Option_C,Option_D,Correct_Option,Answer_Explanation,Probe_Type,TLG_Key_Idea_Ref,Alternative_Conception_Ref,Diagnostic_Use,Source_Note

FIELD RULES
- Correct_Option: A, B, C or D.
- Probe_Type: Direct concept, Application, or Misconception probe.
- Diagnostic_Use: {diagnostic_use}.
- Source_Note: a brief source pointer so the teacher can audit the item.
- Leave TLG references blank when they are not explicitly supported by the source.
- Do not add prose before or after the CSV.
"""
