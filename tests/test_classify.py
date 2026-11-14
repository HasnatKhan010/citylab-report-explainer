from decimal import Decimal
from pathlib import Path

from core.classify import BOUNDARY_ASSUMPTION, classify_result
from core.ingest import load_corpus
from core.ranges import select_range

DATA = Path(__file__).resolve().parents[1] / "lab_reports"


def test_range_endpoints_are_normal_including_biochemistry():
    corpus = load_corpus(DATA)
    alt = classify_result("SGPT", Decimal("45"), "U/L", 35, "female", corpus)
    cholesterol = classify_result("Cholesterol", Decimal("200"), "mg/dL", 55, "female", corpus)
    assert alt["status"] == "normal"
    assert cholesterol["status"] == "normal"
    assert BOUNDARY_ASSUMPTION in alt["trace"]
    assert BOUNDARY_ASSUMPTION in alt["explanation"]
    assert BOUNDARY_ASSUMPTION in cholesterol["trace"]


def test_age_and_sex_interval_boundaries():
    corpus = load_corpus(DATA)
    assert select_range("ALT", 18, "female", corpus).low == Decimal("7")
    assert select_range("ALT", 100, "female", corpus).high == Decimal("45")
    assert select_range("AST", 18, "male", corpus).high == Decimal("48")
    assert select_range("AST", 100, "female", corpus).high == Decimal("43")
    assert select_range("ALT", 101, "female", corpus) is None


def test_urgent_thresholds_are_strict_and_urgent_overrides_range():
    corpus = load_corpus(DATA)
    assert classify_result("Hemoglobin", Decimal("6.9"), "g/dL", 42, "female", corpus)["status"] == "urgent"
    assert classify_result("Hemoglobin", Decimal("7.0"), "g/dL", 42, "female", corpus)["status"] == "low"
    assert classify_result("Fasting Blood Sugar", Decimal("300"), "mg/dL", 45, "male", corpus)["status"] == "high"
    assert classify_result("Platelet Count", Decimal("50000"), "cells/mcL", 42, "female", corpus)["status"] == "low"
    assert classify_result("ALT", Decimal("1000"), "U/L", 48, "male", corpus)["status"] == "high"


def test_unknown_test_and_unsupported_unit_cannot_be_classified():
    corpus = load_corpus(DATA)
    unknown = classify_result("Serum Ferritin", Decimal("25"), "ng/mL", 22, "female", corpus)
    unsupported = classify_result("Fasting Blood Sugar", Decimal("6.0"), "IU/mL", 50, "male", corpus)
    assert unknown["status"] == "cannot_classify"
    assert unsupported["status"] == "cannot_classify"
    assert "no exact match" in unknown["reason"]
    assert "cannot be matched or converted" in unsupported["reason"]


def test_mmol_glucose_is_converted_before_comparison_and_shows_the_working():
    corpus = load_corpus(DATA)
    row = classify_result("Fasting Blood Sugar", Decimal("6.0"), "mmol/L", 50, "male", corpus)
    assert row["status"] == "high"
    assert row["converted_value"] == Decimal("108.11")
    assert row["converted_unit"] == "mg/dL"
    shown = row["conversion_shown"]
    assert shown["factor"] == Decimal("18.0182")
    assert shown["working"] == "6.0 mmol/L x 18.0182 = 108.11 mg/dL"
    assert "standard constant" in shown["source_file"]
    assert any("Converted" in step for step in row["trace"])


def test_interchangeable_microlitre_spellings_need_no_factor():
    corpus = load_corpus(DATA)
    for unit in ("cells/mcL", "cells/uL", "cells/µL"):
        row = classify_result("Platelet Count", Decimal("120000"), unit, 42, "female", corpus)
        assert row["status"] == "low", unit
        assert row["conversion_shown"] is None, unit


def test_value_exactly_on_a_critical_limit_keeps_its_status_and_warns():
    corpus = load_corpus(DATA)
    row = classify_result("Hemoglobin", Decimal("7.0"), "g/dL", 42, "female", corpus)
    assert row["status"] == "low"
    assert row["on_critical_limit"] is True
    assert "see a doctor today" in row["explanation"]


def test_panel_scope_resolves_a_short_urine_test_name():
    corpus = load_corpus(DATA)
    scoped = classify_result("pH Level", Decimal("5.5"), "", 19, "female", corpus, "report_P008_Haley_Urine")
    unscoped = classify_result("pH Level", Decimal("5.5"), "", 19, "female", corpus)
    assert scoped["canonical_name"] == "Urine pH"
    assert scoped["status"] == "normal"
    assert scoped["name_match"]["method"] == "panel_scope"
    assert unscoped["status"] == "cannot_classify"
