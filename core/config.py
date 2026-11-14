"""Deterministic classification configuration."""

from decimal import Decimal

from core.models import Corpus, UnitConversion

# The hematology sheet says both endpoints are normal. The other sheets are silent;
# this documented convention is applied consistently to every numeric range.
ENDPOINTS_INCLUSIVE = True

# The urgent table states "Less than" / "Greater than", so the status comparison stays
# strict. The same file's prose asks for a warning when a result "hit[s] or pass[es]" a
# threshold, so a value sitting exactly on a limit still raises the warning below.
URGENT_STATUS_IS_STRICT = True

STANDARD_SOURCE = "documented standard constant (not from the organizer files)"

# The organizer files supply no factor table, but the problem statement and the corpus
# README both require unit conversion ("different units (e.g., mmol/L instead of
# mg/dL)"). These factors are published analytical constants, each stated with the
# derivation it comes from, and every use of one is labelled in the result trace.
STANDARD_CONVERSIONS: list[UnitConversion] = [
    UnitConversion(
        analyte="Fasting Blood Sugar", from_unit="mmol/L", to_unit="mg/dL",
        factor=Decimal("18.0182"), source_file=STANDARD_SOURCE,
        source_row="Glucose molar mass 180.156 g/mol, so 1 mmol/L = 18.0182 mg/dL.",
    ),
    UnitConversion(
        analyte="Cholesterol", from_unit="mmol/L", to_unit="mg/dL",
        factor=Decimal("38.67"), source_file=STANDARD_SOURCE,
        source_row="Cholesterol molar mass 386.65 g/mol, so 1 mmol/L = 38.67 mg/dL.",
    ),
    UnitConversion(
        analyte=None, from_unit="g/L", to_unit="g/dL", factor=Decimal("0.1"),
        source_file=STANDARD_SOURCE, source_row="One litre is 10 decilitres, so 1 g/L = 0.1 g/dL.",
    ),
    UnitConversion(
        analyte=None, from_unit="10^9/L", to_unit="cells/mcL", factor=Decimal("1000"),
        source_file=STANDARD_SOURCE,
        source_row="One microlitre is 10^-6 litre, so 1 x10^9/L = 1000 cells/mcL.",
    ),
    UnitConversion(
        analyte=None, from_unit="10^3/uL", to_unit="cells/mcL", factor=Decimal("1000"),
        source_file=STANDARD_SOURCE, source_row="10^3 per microlitre is 1000 cells/mcL.",
    ),
    UnitConversion(
        analyte=None, from_unit="K/uL", to_unit="cells/mcL", factor=Decimal("1000"),
        source_file=STANDARD_SOURCE, source_row="K per microlitre means thousands, so 1 K/uL = 1000 cells/mcL.",
    ),
    UnitConversion(
        analyte=None, from_unit="uIU/mL", to_unit="mIU/L", factor=Decimal("1"),
        source_file=STANDARD_SOURCE, source_row="1 uIU/mL and 1 mIU/L are the same concentration.",
    ),
]


def unit_conversion_table(corpus: Corpus) -> list[UnitConversion]:
    """Factors parsed from organizer files first, then documented standard constants."""
    return [*corpus.conversions, *STANDARD_CONVERSIONS]
