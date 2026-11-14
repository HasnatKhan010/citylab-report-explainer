from pathlib import Path

from core.ingest import load_corpus
from core.plain_language import _ANALYTES, describes, doctor_questions, result_meaning
from core.service import analyze_patient
from llm.validator import _DIAGNOSIS_PATTERNS

DATA = Path(__file__).resolve().parents[1] / "lab_reports"


def test_every_analyte_with_a_range_has_plain_language_wording():
    corpus = load_corpus(DATA)
    missing = sorted({row.analyte for row in corpus.ranges} - set(_ANALYTES))
    assert missing == []


def test_descriptions_exist_in_both_languages_and_say_nothing_for_unknown_tests():
    assert "oxygen" in describes("Hemoglobin")
    assert describes("Hemoglobin", "ur") != describes("Hemoglobin")
    assert "do not say" in describes("Serum Ferritin")
    assert "do not say" not in describes("Serum Ferritin", "ur")


def test_no_curated_sentence_uses_diagnosis_wording():
    texts = [
        text
        for entry in _ANALYTES.values()
        for wording in entry.values()
        for text in wording.values()
    ]
    texts += [result_meaning("Hemoglobin", status) for status in ("normal", "low", "high", "urgent")]
    offenders = [text for text in texts if any(p.search(text) for p in _DIAGNOSIS_PATTERNS)]
    assert offenders == []


def test_urgent_meaning_keeps_the_phrase_the_files_ask_for():
    assert "see a doctor today" in result_meaning("Hemoglobin", "urgent")


def test_doctor_questions_are_three_to_five_and_lead_with_urgent_results():
    rows = [
        {"status": "low", "canonical_name": "Platelet Count"},
        {"status": "urgent", "canonical_name": "Hemoglobin"},
    ]
    questions = doctor_questions(rows)
    assert 3 <= len(questions) <= 5
    assert questions[0].startswith("My Hemoglobin")
    assert doctor_questions([{"status": "normal", "canonical_name": "TSH"}]) == []


def test_questions_stay_within_bounds_for_a_report_full_of_flagged_results():
    rows = [{"status": "high", "canonical_name": f"Analyte {i}"} for i in range(9)]
    assert len(doctor_questions(rows)) == 5


def test_analysis_explains_each_test_in_the_requested_language():
    english = analyze_patient("P004")
    urdu = analyze_patient("P004", language="ur")
    assert all(row["what_it_measures"] for row in english["tests"])
    assert all(row["what_this_result_can_mean"] for row in english["tests"])
    assert urdu["tests"][0]["what_it_measures"] != english["tests"][0]["what_it_measures"]
    assert 3 <= len(urdu["doctor_questions"]) <= 5
