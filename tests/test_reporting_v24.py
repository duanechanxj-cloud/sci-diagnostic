import pandas as pd

from src.gemini_analysis import prepare_anonymous_question_evidence
from src.reporting import make_topic_performance_chart, generate_reports_for_class


def test_gemini_evidence_excludes_class_index_and_ids():
    rows = pd.DataFrame([{
        "Response_ID":"R1", "Pupil_Key":"P3U_17", "Class_Code":"P3U", "Class_Name":"3 Unity",
        "Index_Number":"17", "Timestamp":"2026-08-30", "Question_ID":"Q1", "Topic_Code":"T1",
        "LO_ID":"L1", "Question_Text":"Demo?", "Student_Response":"B", "Correct_Option":"A",
        "Correct":False, "Official Topic":"Demo topic", "Official Learning Outcome":"Demo LO",
    }])
    blob = str(prepare_anonymous_question_evidence(rows))
    for forbidden in ["P3U_17", "3 Unity", "2026-08-30", "Response_ID", "Index_Number"]:
        assert forbidden not in blob


def test_topic_chart_bytes():
    topic = pd.DataFrame([
        {"Topic_Code":"T1", "Official Topic":"Magnets", "Questions":10, "Correct":7, "Percent_Correct":70.0},
        {"Topic_Code":"T2", "Official Topic":"Materials", "Questions":8, "Correct":6, "Percent_Correct":75.0},
    ])
    assert len(make_topic_performance_chart(topic).getvalue()) > 1000


def test_reports_use_class_and_index_and_do_not_collide(tmp_path):
    lo = pd.DataFrame([
        {"Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"17", "Pupil_Key":"P3U_17", "Official Topic":"Magnets", "LO_ID":"L1", "Official Learning Outcome":"Demo", "Correct":1, "Questions":1, "Percent_Correct":100.0},
        {"Response_ID":"R2", "Class_Name":"3 Wonder", "Index_Number":"17", "Pupil_Key":"P3W_17", "Official Topic":"Magnets", "LO_ID":"L1", "Official Learning Outcome":"Demo", "Correct":0, "Questions":1, "Percent_Correct":0.0},
    ])
    topic = pd.DataFrame([
        {"Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"17", "Pupil_Key":"P3U_17", "Topic_Code":"T1", "Official Topic":"Magnets", "Questions":1, "Correct":1, "Percent_Correct":100.0},
        {"Response_ID":"R2", "Class_Name":"3 Wonder", "Index_Number":"17", "Pupil_Key":"P3W_17", "Topic_Code":"T1", "Official Topic":"Magnets", "Questions":1, "Correct":0, "Percent_Correct":0.0},
    ])
    paths = generate_reports_for_class(lo, topic, tmp_path, "Demo Diagnostic")
    assert len(paths) == 2
    assert paths[0].name != paths[1].name
    assert all(p.exists() for p in paths)


def test_report_uses_compact_matrix_general_next_steps_and_two_page_limit(tmp_path):
    from pypdf import PdfReader
    from src.gemini_analysis import DiagnosticReportAnalysis
    from src.reporting import generate_student_pdf, report_zip_filename, REPORT_BODY_FONT_SIZE

    lo = pd.DataFrame([
        {"Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"12", "Pupil_Key":"P3U_12", "Topic_Code":"P3-DIV-LNL", "Official Topic":"Diversity of Living and Non-Living Things (General characteristics and classification)", "LO_ID":"L1", "Official Learning Outcome":"Describe the characteristics of living things.", "Correct":0, "Questions":1, "Percent_Correct":0.0},
        {"Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"12", "Pupil_Key":"P3U_12", "Topic_Code":"P3-DIV-LNL", "Official Topic":"Diversity of Living and Non-Living Things (General characteristics and classification)", "LO_ID":"L2", "Official Learning Outcome":"Recognise some broad groups of living things based on similarities and differences.", "Correct":1, "Questions":1, "Percent_Correct":100.0},
        {"Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"12", "Pupil_Key":"P3U_12", "Topic_Code":"P3-INT-MAG", "Official Topic":"Interaction of Forces (Magnets)", "LO_ID":"L3", "Official Learning Outcome":"Identify the characteristics of magnets.", "Correct":1, "Questions":1, "Percent_Correct":100.0},
    ])
    topic = pd.DataFrame([
        {"Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"12", "Pupil_Key":"P3U_12", "Topic_Code":"P3-DIV-LNL", "Official Topic":"Diversity of Living and Non-Living Things (General characteristics and classification)", "Questions":2, "Correct":1, "Percent_Correct":50.0},
        {"Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"12", "Pupil_Key":"P3U_12", "Topic_Code":"P3-INT-MAG", "Official Topic":"Interaction of Forces (Magnets)", "Questions":1, "Correct":1, "Percent_Correct":100.0},
    ])
    ai = DiagnosticReportAnalysis(
        response_pattern_summary="The responses suggest secure evidence for magnets, while the living-things item may benefit from a fresh check.",
        concepts_to_revisit=["Characteristics of living things"],
        suggested_next_steps=["Revisit the relevant notes, then explain one living and one non-living example aloud."],
    )
    path = tmp_path / "report.pdf"
    generate_student_pdf(lo, topic, path, "Primary Science Learning Diagnostic", "WA3 Revision", gemini_analysis=ai)
    reader = PdfReader(str(path))
    assert len(reader.pages) <= 2
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Living & Non-Living" in text
    assert "Suggested next steps" in text
    assert "How parents can help" not in text
    assert REPORT_BODY_FONT_SIZE == 10
    assert report_zip_filename("WA3 Revision") == "science_diagnostic_reports_WA3_Revision.zip"
    assert report_zip_filename("") == "science_diagnostic_reports.zip"


def test_representative_large_p3_report_still_fits_two_pages(tmp_path):
    from pypdf import PdfReader
    from src.gemini_analysis import DiagnosticReportAnalysis
    from src.reporting import generate_student_pdf

    topics_meta = [
        ("P3-DIV-LNL", "Diversity of Living and Non-Living Things (General characteristics and classification)"),
        ("P3-DIV-MAT", "Diversity of Materials"),
        ("P3-CYC-LC", "Cycles in Plants and Animals (Life Cycles)"),
        ("P3-INT-MAG", "Interaction of Forces (Magnets)"),
    ]
    lo_rows = []
    for ti, (topic_code, official_topic) in enumerate(topics_meta):
        for j in range(3):
            lo_rows.append({
                "Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"39", "Pupil_Key":"P3U_39",
                "Topic_Code":topic_code, "Official Topic":official_topic, "LO_ID":f"L{ti}{j}",
                "Official Learning Outcome":f"Explain and apply Science concept {j + 1} for {official_topic}.",
                "Correct":1 if j else 0, "Questions":2, "Percent_Correct":50.0,
            })
    lo = pd.DataFrame(lo_rows)
    topic = pd.DataFrame([
        {"Response_ID":"R1", "Class_Name":"3 Unity", "Index_Number":"39", "Pupil_Key":"P3U_39",
         "Topic_Code":code, "Official Topic":name, "Questions":10, "Correct":correct, "Percent_Correct":correct*10.0}
        for (code, name), correct in zip(topics_meta, [6, 8, 7, 9])
    ])
    ai = DiagnosticReportAnalysis(
        response_pattern_summary="The responses show stronger evidence on several tested ideas, with a smaller number of concepts that may benefit from targeted revision. The pattern should be checked again with fresh questions before drawing firm conclusions.",
        concepts_to_revisit=["Concept one", "Concept two", "Concept three", "Concept four"],
        suggested_next_steps=[
            "Revisit the relevant school notes and explain each target concept aloud.",
            "Use fresh examples and non-examples to check transfer.",
            "Attempt a short set of new questions after revision.",
        ],
    )
    path = tmp_path / "large_report.pdf"
    generate_student_pdf(lo, topic, path, "Primary Science Learning Diagnostic", "Pre-EOY Diagnostic", include_score=True, gemini_analysis=ai)
    assert len(PdfReader(str(path)).pages) <= 2


def test_gemini_model_constants_are_safe_and_default_to_flash_lite():
    from src.gemini_analysis import DEFAULT_GEMINI_MODEL, GEMINI_MODEL_OPTIONS
    assert DEFAULT_GEMINI_MODEL == "gemini-3.5-flash-lite"
    assert DEFAULT_GEMINI_MODEL in GEMINI_MODEL_OPTIONS.values()
    assert len(GEMINI_MODEL_OPTIONS) == 4
    assert len(set(GEMINI_MODEL_OPTIONS.values())) == 4
