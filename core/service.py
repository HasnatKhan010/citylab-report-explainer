"""Public patient analysis and files-only follow-up question functions."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from core.classify import classify_result
from core.ingest import DEFAULT_DATA_DIR, load_corpus, parse_report_text
from core.models import Corpus, PatientReport
from core.names import canonical_name, normalize_name
from core.plain_language import ATTRIBUTION, describes, doctor_questions, result_meaning, urgent_banner
from core.ranges import supported_age_bounds


@lru_cache(maxsize=1)
def _default_corpus() -> Corpus:
    return load_corpus(DEFAULT_DATA_DIR)


def get_corpus() -> Corpus:
    """Return the lazily parsed default organizer corpus."""
    return _default_corpus()


def _status_for_demographics(patient: PatientReport) -> tuple[bool, str | None]:
    missing: list[str] = []
    if patient.age is None:
        missing.append("age")
    if patient.sex is None:
        missing.append("biological sex at birth")
    if not missing:
        return False, None
    requested = " and ".join(missing)
    return True, f"Please provide the patient's {requested}. The safety rules say not to guess when demographics are missing or invalid."


def _clarification_result(original: str, value, unit: str, canonical: str | None, question: str) -> dict:
    return {
        "original_name": original,
        "canonical_name": canonical,
        "value": value,
        "original_unit": unit,
        "converted_value": value,
        "converted_unit": unit,
        "conversion_shown": None,
        "range_used": None,
        "status": "needs_clarification",
        "urgent_flag": False,
        "on_critical_limit": False,
        "name_match": {"method": "exact" if canonical else "unmatched", "detail": ""},
        "trace": ["Safety rule: 1_lab_safety_rules.md, Core Operational Directives, rule 3."],
        "explanation": question,
        "reason": question,
    }


def analyze_patient(patient_id: str, corpus: Corpus | None = None, language: str = "en") -> dict:
    """Analyze only the requested active patient from the organizer corpus."""
    corpus = corpus or _default_corpus()
    key = patient_id.strip().upper()
    patient = corpus.patients.get(key)
    if patient is None:
        raise KeyError(f"Unknown patient ID: {patient_id}")
    return _analyze_report(patient, corpus, language)


def analyze_report_text(report_text: str, corpus: Corpus | None = None, language: str = "en") -> dict:
    """Analyze a report pasted by the user against the same reference files.

    The reference sheets, aliases, and urgent limits still come only from the organizer
    corpus; the pasted text supplies the results and demographics and nothing else.
    """
    corpus = corpus or _default_corpus()
    patient = parse_report_text(report_text, source_file="pasted report", require_name=False)
    if patient is None or not patient.results:
        raise ValueError(
            "No test results could be read from the pasted report. Each result needs a test "
            "name and a value, for example 'Hemoglobin: 13.5 g/dL'."
        )
    analysis = _analyze_report(patient, corpus, language)
    analysis["source_file"] = "pasted report"
    return analysis


def _analyze_report(patient: PatientReport, corpus: Corpus, language: str = "en") -> dict:
    needs_clarification, question = _status_for_demographics(patient)
    bounds = supported_age_bounds(corpus)
    age_outside = bool(bounds and patient.age is not None and not (bounds[0] <= patient.age <= bounds[1]))
    rows: list[dict] = []
    cannot: list[dict] = []

    for item in patient.results:
        if needs_clarification:
            row = _clarification_result(item.original_name, item.value, item.unit, canonical_name(item.original_name, corpus, patient.panel), question or "")
        elif age_outside:
            canonical = canonical_name(item.original_name, corpus, patient.panel)
            reason = f"Age {patient.age} is outside the age bands supported by the files ({bounds[0]}-{bounds[1]} years)."
            row = {
                "original_name": item.original_name,
                "canonical_name": canonical,
                "value": item.value,
                "original_unit": item.unit,
                "converted_value": item.value,
                "converted_unit": item.unit,
                "conversion_shown": None,
                "range_used": None,
                "status": "cannot_classify",
                "urgent_flag": False,
                "on_critical_limit": False,
                "name_match": {"method": "exact" if canonical else "unmatched", "detail": ""},
                "trace": ["Age-band validation: no source range covers this age."],
                "explanation": "This result cannot be classified from the files because the patient's age is outside every listed age band.",
                "reason": reason,
            }
        else:
            # The demographic gate above guarantees age and sex are present here.
            row = classify_result(item.original_name, item.value, item.unit, patient.age, patient.sex, corpus, patient.panel)  # type: ignore[arg-type]
        row["what_it_measures"] = describes(row["canonical_name"], language)
        row["what_this_result_can_mean"] = result_meaning(row["canonical_name"], row["status"], language)
        rows.append(row)
        if row["status"] == "cannot_classify":
            cannot.append({"test": row["original_name"], "reason": row["reason"]})

    urgent_warnings = [
        {
            "test": row["canonical_name"] or row["original_name"],
            "message": urgent_banner("crossed", language),
        }
        for row in rows if row["urgent_flag"]
    ]
    urgent_warnings.extend(
        {
            "test": row["canonical_name"] or row["original_name"],
            "message": urgent_banner("on_limit", language),
        }
        for row in rows if row.get("on_critical_limit") and not row["urgent_flag"]
    )
    return {
        "patient_id": patient.patient_id,
        "patient_name": patient.name,
        "age": patient.age,
        "biological_sex": patient.sex,
        "source_file": patient.source_file,
        "needs_clarification": needs_clarification,
        "clarification_question": question,
        "tests": rows,
        "cannot_classify": cannot,
        "doctor_questions": doctor_questions(rows, language),
        "urgent_warnings": urgent_warnings,
        "wording_note": ATTRIBUTION,
        "disclaimer": "This tool compares results with the supplied files and does not diagnose. Only a licensed doctor can diagnose.",
    }


def _other_patient_mentioned(patient_id: str, question: str, corpus: Corpus) -> str | None:
    active = patient_id.upper()
    for report in corpus.patients.values():
        if report.patient_id == active:
            continue
        if re.search(rf"(?<![A-Z0-9]){re.escape(report.patient_id)}(?![A-Z0-9])", question, re.I):
            return report.patient_id
        normalized_question = normalize_name(question)
        name_parts = [normalize_name(part) for part in report.name.split() if len(part) >= 4]
        if normalize_name(report.name) in normalized_question or any(part in normalized_question for part in name_parts):
            return report.patient_id
    return None


def answer_question(patient_id: str, question: str, corpus: Corpus | None = None, language: str = "en") -> dict:
    """Answer from the active patient's parsed report, ranges, and glossary only."""
    corpus = corpus or _default_corpus()
    key = patient_id.strip().upper()
    if key not in corpus.patients:
        raise KeyError(f"Unknown patient ID: {patient_id}")
    other = _other_patient_mentioned(key, question, corpus)
    if other:
        return {
            "patient_id": key,
            "refused": True,
            "answer": "I can only discuss the active patient's report and cannot provide another patient's results.",
            "citations": [{"source_file": "1_lab_safety_rules.md", "rule": "Core Operational Directives, rule 1"}],
        }

    analysis = analyze_patient(key, corpus, language)
    normalized_question = normalize_name(question)
    matched = []
    for row in analysis["tests"]:
        candidates = [row["original_name"], row["canonical_name"]]
        if any(candidate and normalize_name(candidate) in normalized_question for candidate in candidates):
            matched.append(row)

    if matched:
        if re.search(r"\b(?:meaning|means|mean|definition|define|function of|measure[sd]?)\b", question, re.I):
            answer = " ".join(
                f"{row['original_name']}: {row['what_it_measures']} {row['what_this_result_can_mean']}"
                for row in matched
            )
            citations = [
                {"source_file": analysis["source_file"]},
                {"source_file": "2_medical_glossary.md", "detail": "Alias mapping only."},
                {"source_file": "core/plain_language.py", "detail": ATTRIBUTION},
            ]
        else:
            parts = [
                f"{row['original_name']}: {row['value']} {row['original_unit']} - {row['status']} ({row['reason']})"
                for row in matched
            ]
            answer = " ".join(parts)
            citations = [{"source_file": analysis["source_file"]}]
            citations.extend(
                {"source_file": row["range_used"]["source_file"], "range_row": row["trace"][1] if len(row["trace"]) > 1 else ""}
                for row in matched if row.get("range_used")
            )
        return {"patient_id": key, "refused": False, "answer": answer, "citations": citations}

    if re.search(r"\b(?:my results|my tests|my report|all results|all tests)\b", question, re.I):
        answer = "; ".join(
            f"{row['original_name']}: {row['value']} {row['original_unit']} ({row['status']})"
            for row in analysis["tests"]
        ) or "No test results were parsed from the active patient's report."
        return {"patient_id": key, "refused": False, "answer": answer, "citations": [{"source_file": analysis["source_file"]}]}

    return {
        "patient_id": key,
        "refused": False,
        "answer": "That information is not covered in the files.",
        "citations": [{"source_file": "2_medical_glossary.md", "detail": "No supporting explanation was found."}],
    }

