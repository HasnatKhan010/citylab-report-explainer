"""Exact, files-derived test-name matching."""

from __future__ import annotations

import re
from typing import NamedTuple

from core.models import Corpus

# Words a report adds around a test name without changing which test it is.
_NOISE_WORDS = {"level", "levels", "value", "values", "result", "results", "test", "reading"}


class NameMatch(NamedTuple):
    canonical: str | None
    method: str
    detail: str


def normalize_name(name: str) -> str:
    """Ignore case, whitespace, and punctuation while preserving all letters/digits."""
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def _without_noise_words(name: str) -> str:
    kept = [word for word in re.split(r"[^A-Za-z0-9]+", name) if word and word.casefold() not in _NOISE_WORDS]
    return normalize_name(" ".join(kept))


def _canonical_by_key(corpus: Corpus) -> dict[str, str]:
    return {normalize_name(item.analyte): item.analyte for item in corpus.ranges}


def _panel_tokens(panel: str) -> set[str]:
    return {token.casefold() for token in re.split(r"[^A-Za-z0-9]+", panel) if token}


def resolve_name(name: str, corpus: Corpus, panel: str = "") -> NameMatch:
    """Resolve a reported test name to a canonical analyte, reporting how it matched.

    Only three sources are used: the analyte names in the range sheets, the glossary
    aliases, and - when the report itself identifies a panel - the qualifier that the
    range sheets already put in front of an analyte name, such as "Urine pH".
    """
    canonical_by_key = _canonical_by_key(corpus)
    key = normalize_name(name)
    if key in canonical_by_key:
        return NameMatch(canonical_by_key[key], "exact", "Name matches an analyte in the range sheets.")

    aliases = {normalize_name(alias): canonical for alias, canonical in corpus.aliases.items()}
    target = aliases.get(key)
    if target is not None:
        canonical = canonical_by_key.get(normalize_name(target), target)
        return NameMatch(canonical, "glossary_alias", f"2_medical_glossary.md maps {name} to {target}.")

    tokens = _panel_tokens(panel)
    if tokens:
        stripped = _without_noise_words(name)
        for analyte, canonical in ((normalize_name(a), a) for a in canonical_by_key.values()):
            parts = canonical.split()
            if len(parts) < 2 or parts[0].casefold() not in tokens:
                continue
            remainder = _without_noise_words(" ".join(parts[1:]))
            if remainder and remainder == stripped:
                return NameMatch(
                    canonical,
                    "panel_scope",
                    f"The report identifies the {parts[0]} panel, and the range sheets list this test as {canonical}.",
                )
    return NameMatch(None, "unmatched", "No analyte name or glossary alias matches.")


def canonical_name(name: str, corpus: Corpus, panel: str = "") -> str | None:
    """Resolve exact normalized names, glossary aliases, and panel-scoped names."""
    return resolve_name(name, corpus, panel).canonical
