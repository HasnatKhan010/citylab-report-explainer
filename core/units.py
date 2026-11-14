"""Unit checking and conversions using explicit, cited factors."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import NamedTuple

from core.models import UnitConversion


class Conversion(NamedTuple):
    compatible: bool
    value: Decimal | str
    unit: str
    shown: bool
    factor: Decimal | None
    source: UnitConversion | None = None


# mcL, uL, and the micro sign spell the same microlitre; reports mix all three.
_MICRO_SIGNS = ("\u00b5", "\u03bc")


def normalize_unit(unit: str) -> str:
    """Fold case and punctuation, and treat mc/u/micro-sign spellings as one unit."""
    text = unit.casefold()
    for sign in _MICRO_SIGNS:
        text = text.replace(sign, "u")
    text = re.sub(r"[^a-z0-9]", "", text)
    text = text.replace("mc", "u")
    # A leading multiplication marker, as in "x10^9/L", carries no unit meaning.
    return re.sub(r"^x", "", text)


def tidy(value: Decimal) -> Decimal:
    """Keep converted values readable without changing which side of a limit they fall on."""
    quantized = value.quantize(Decimal("0.01"))
    stripped = quantized.normalize()
    return stripped if stripped.as_tuple().exponent <= 0 else stripped.quantize(Decimal(1))


def convert_value(
    value: Decimal | str,
    from_unit: str,
    to_unit: str,
    analyte: str,
    conversions: list[UnitConversion],
) -> Conversion:
    """Convert only for identical units or an explicit factor supplied by the caller.

    Reverse conversion uses the reciprocal of an explicit forward factor. Every factor
    carries its own source, so the trace can state where the number came from.
    """
    if normalize_unit(from_unit) == normalize_unit(to_unit):
        return Conversion(True, value, to_unit, False, None, None)
    if not isinstance(value, Decimal):
        return Conversion(False, value, from_unit, False, None, None)

    wanted_from = normalize_unit(from_unit)
    wanted_to = normalize_unit(to_unit)
    wanted_test = re.sub(r"[^a-z0-9]", "", analyte.casefold())
    for entry in conversions:
        if entry.analyte and re.sub(r"[^a-z0-9]", "", entry.analyte.casefold()) != wanted_test:
            continue
        source = normalize_unit(entry.from_unit)
        target = normalize_unit(entry.to_unit)
        if source == wanted_from and target == wanted_to:
            factor = entry.factor
        elif source == wanted_to and target == wanted_from and entry.factor != 0:
            factor = Decimal(1) / entry.factor
        else:
            continue
        return Conversion(True, tidy(value * factor), to_unit, True, factor, entry)
    return Conversion(False, value, from_unit, False, None, None)
