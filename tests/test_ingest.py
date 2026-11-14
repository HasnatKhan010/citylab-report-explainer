from pathlib import Path

from core.ingest import load_corpus

DATA = Path(__file__).resolve().parents[1] / "lab_reports"


def test_loads_all_reports_and_reference_files():
    corpus = load_corpus(DATA)
    assert len(corpus.patients) == 14
    assert len(corpus.ranges) == 13
    assert len(corpus.urgent_thresholds) == 4
    assert len(corpus.conversions) == 0
    assert corpus.patients["P003"].age is None
    assert corpus.patients["P003"].sex is None
    assert corpus.patients["P012"].age == 32
    assert corpus.patients["P012"].sex is None


def test_parses_bullets_tables_plain_labels_and_arrows():
    corpus = load_corpus(DATA)
    assert [(r.original_name, str(r.value), r.unit) for r in corpus.patients["P001"].results] == [
        ("Hemoglobin", "13.5", "g/dL"),
        ("WBC", "6000", "cells/mcL"),
    ]
    assert [(r.original_name, str(r.value), r.unit) for r in corpus.patients["P002"].results] == [
        ("SGPT", "45", "U/L"),
    ]
    assert corpus.patients["P003"].results[0].original_name == "Fasting Blood Sugar"
    assert corpus.patients["P007"].results[0].original_name == "TSH"
    assert [(r.original_name, str(r.value)) for r in corpus.patients["P008"].results] == [
        ("pH Level", "5.5"),
        ("Protein", "Negative"),
    ]


def test_report_appendices_are_not_ingested_as_results():
    corpus = load_corpus(DATA)
    for report in corpus.patients.values():
        assert all("appendix" not in result.original_name.casefold() for result in report.results)
        assert all("medical record" not in result.original_name.casefold() for result in report.results)

