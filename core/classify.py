"""Deterministic classification rules. No LLM or external ranges are used."""

from __future__ import annotations

from decimal import Decimal

from core.config import ENDPOINTS_INCLUSIVE, unit_conversion_table
from core.models import Corpus, ReferenceRange, UrgentThreshold
from core.names import resolve_name
from core.ranges import categorical_reference, select_range
from core.units import convert_value, normalize_unit

BOUNDARY_ASSUMPTION = "sheet does not state a boundary rule; hematology convention applied."
CRITICAL_LIMIT_NOTE = (
    "This result sits exactly on a critical limit listed in the files. The urgent-values "
    "directive asks for a warning when a result hits or passes a limit, so please see a "
    "doctor today, even though the limit's own condition is a strict comparison."
)


def _threshold_applies(item: UrgentThreshold, analyte: str, unit: str) -> bool:
    return (
        item.analyte.casefold() == analyte.casefold()
        and normalize_unit(item.unit) == normalize_unit(unit)
    )


def _crossed_threshold(analyte: str, unit: str, value: Decimal, thresholds: list[UrgentThreshold]) -> UrgentThreshold | None:
    """Apply the strict comparison the urgent table states for each limit."""
    for item in thresholds:
        if not _threshold_applies(item, analyte, unit):
            continue
        if item.operator == "lt" and value < item.value:
            return item
        if item.operator == "gt" and value > item.value:
            return item
    return None


def _on_threshold(analyte: str, unit: str, value: Decimal, thresholds: list[UrgentThreshold]) -> UrgentThreshold | None:
    for item in thresholds:
        if _threshold_applies(item, analyte, unit) and value == item.value:
            return item
    return None


def _result_shell(original_name: str, value: Decimal | str, unit: str) -> dict:
    return {
        "original_name": original_name,
        "canonical_name": None,
        "value": value,
        "original_unit": unit,
        "converted_value": value,
        "converted_unit": unit,
        "conversion_shown": None,
        "range_used": None,
        "status": "cannot_classify",
        "urgent_flag": False,
        "on_critical_limit": False,
        "name_match": {"method": "unmatched", "detail": ""},
        "trace": [],
        "explanation": "",
        "reason": "",
    }


def _range_dict(row: ReferenceRange) -> dict:
    return {
        "low": row.low,
        "high": row.high,
        "age_band": {"min": row.age_min, "max": row.age_max},
        "sex": row.sex,
        "source_file": row.source_file,
    }


def classify_result(
    original_name: str,
    value: Decimal | str,
    unit: str,
    age: int,
    sex: str,
    corpus: Corpus,
    panel: str = "",
) -> dict:
    result = _result_shell(original_name, value, unit)
    match = resolve_name(original_name, corpus, panel)
    canonical = match.canonical
    result["canonical_name"] = canonical
    result["name_match"] = {"method": match.method, "detail": match.detail}
    if canonical is None:
        result["reason"] = "Test name has no exact match or alias in the organizer files."
        result["explanation"] = "This test cannot be classified from the files because its name has no listed range or alias."
        return result

    row = select_range(canonical, age, sex, corpus)
    if row is None:
        result["reason"] = f"No reference range for {canonical} at age {age} and sex {sex} is present in the files."
        result["explanation"] = "This test cannot be classified from the files because no matching range was found."
        return result
    result["range_used"] = _range_dict(row)
    trace = [f"Name match ({match.method}): {match.detail}", f"Range source: {row.source_file}", f"Range row: {row.source_row}"]
    if row.source_file != "4_ranges_hematology.md":
        trace.append(BOUNDARY_ASSUMPTION)

    conversion = convert_value(value, unit, row.unit, canonical, unit_conversion_table(corpus))
    if not conversion.compatible:
        result["trace"] = trace + ["No conversion factor supports this unit."]
        result["reason"] = f"Unit {unit or '(not stated)'} cannot be matched or converted to {row.unit or '(no unit stated)'}."
        result["explanation"] = "This result cannot be classified from the files because its unit is unsupported."
        if row.source_file != "4_ranges_hematology.md":
            result["explanation"] += " " + BOUNDARY_ASSUMPTION
        return result

    result["converted_value"] = conversion.value
    result["converted_unit"] = conversion.unit
    if conversion.shown and conversion.source is not None:
        working = f"{value} {unit} x {conversion.factor} = {conversion.value} {conversion.unit}"
        result["conversion_shown"] = {
            "value": value,
            "from": unit,
            "to": conversion.unit,
            "factor": conversion.factor,
            "result": conversion.value,
            "source_file": conversion.source.source_file,
            "basis": conversion.source.source_row,
            "working": working,
        }
        trace.append(
            f"Converted {working} using a factor from {conversion.source.source_file}: {conversion.source.source_row}"
        )

    if isinstance(conversion.value, Decimal):
        urgent = _crossed_threshold(canonical, conversion.unit, conversion.value, corpus.urgent_thresholds)
        if urgent:
            result["status"] = "urgent"
            result["urgent_flag"] = True
            trace.extend([f"Urgent rule: {urgent.source_row}", "Urgent threshold comparison is strict."])
            result["reason"] = "A strict urgent threshold in the dangerous-values file was crossed."
            result["explanation"] = "The result crosses a critical limit listed in the files. Please see a doctor today."
            if row.source_file != "4_ranges_hematology.md":
                result["explanation"] += " " + BOUNDARY_ASSUMPTION
            result["trace"] = trace
            return result

    if row.low is None and row.high is None:
        expected = categorical_reference(row)
        actual = str(conversion.value).strip().casefold()
        if expected and actual == expected.casefold():
            result["status"] = "normal"
            result["reason"] = f"Value matches the qualitative reference value {expected!r} in the files."
            result["explanation"] = "The reported value matches the qualitative reference value listed in the files."
        else:
            result["reason"] = "The files do not provide a numeric range or a matching qualitative reference value."
            result["explanation"] = "This result cannot be classified from the files."
        trace.append("Compared with the qualitative reference value in the source row.")
    elif not isinstance(conversion.value, Decimal):
        result["reason"] = "A numeric value is required by the listed reference range."
        result["explanation"] = "This result cannot be classified from the files because its value is not numeric."
    else:
        value_num = conversion.value
        low, high = row.low, row.high
        assert low is not None and high is not None
        if ENDPOINTS_INCLUSIVE and low <= value_num <= high:
            result["status"] = "normal"
            result["reason"] = f"Value is within the listed reference interval {low}-{high} {row.unit}."
        elif value_num < low:
            result["status"] = "low"
            result["reason"] = f"Value is below the listed reference interval {low}-{high} {row.unit}."
        else:
            result["status"] = "high"
            result["reason"] = f"Value is above the listed reference interval {low}-{high} {row.unit}."
        status_words = {"normal": "within", "low": "below", "high": "above"}
        result["explanation"] = (
            f"The reported value is {status_words[result['status']]} the range listed in "
            f"{row.source_file}; this comparison is not a diagnosis."
        )
        trace.append(f"Boundary rule: endpoints {'inclusive' if ENDPOINTS_INCLUSIVE else 'exclusive'}.")

        limit = _on_threshold(canonical, conversion.unit, value_num, corpus.urgent_thresholds)
        if limit:
            result["on_critical_limit"] = True
            result["explanation"] += " " + CRITICAL_LIMIT_NOTE
            trace.append(f"Sits exactly on the critical limit: {limit.source_row}")

    if row.source_file != "4_ranges_hematology.md":
        trace.append(BOUNDARY_ASSUMPTION)
        result["explanation"] += " " + BOUNDARY_ASSUMPTION
    result["trace"] = trace
    return result
