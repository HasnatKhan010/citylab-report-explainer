"""Strict JSON, safety, and data-preservation checks for LLM wording."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ExplanationItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    test: str
    explanation: str = Field(min_length=1, max_length=500)


class ExplanationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    explanations: list[ExplanationItem]
    doctor_questions: list[str]


class InvalidLLMOutput(ValueError):
    pass


_DIAGNOSIS_PATTERNS = (
    re.compile(r"\bdiagnos(?:e|ed|is|tic)\b", re.I),
    re.compile(r"\b(?:you|patient)\s+(?:have|has|suffer from|are|is)\b", re.I),
    re.compile(r"\bthis\s+(?:means|shows|proves)\s+(?:you|the patient)\b", re.I),
)


def validate_explanation(raw: str, results: list[dict]) -> ExplanationOutput:
    try:
        parsed: Any = json.loads(raw)
        output = ExplanationOutput.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise InvalidLLMOutput("Response is not the required strict JSON schema.") from exc

    expected_names = [row["original_name"] for row in results]
    actual_names = [item.test for item in output.explanations]
    if actual_names != expected_names:
        raise InvalidLLMOutput("Explanation test names or ordering changed.")
    non_normal = any(row["status"] in {"low", "high", "urgent", "cannot_classify", "needs_clarification"} for row in results)
    if non_normal and not 3 <= len(output.doctor_questions) <= 5:
        raise InvalidLLMOutput("Non-normal results require 3 to 5 doctor questions.")
    if not non_normal and output.doctor_questions:
        raise InvalidLLMOutput("Questions are only allowed for non-normal results.")

    for item, row in zip(output.explanations, results):
        text = item.explanation
        if any(pattern.search(text) for pattern in _DIAGNOSIS_PATTERNS):
            raise InvalidLLMOutput("Diagnosis wording is not allowed.")
        # The structured output must be wording only. Ban figures and unit strings
        # so it cannot restate or silently change the deterministic values.
        if re.search(r"\d", text):
            raise InvalidLLMOutput("Explanation must not restate or change values or units.")
        for unit in (row.get("original_unit", ""), row.get("converted_unit", "")):
            if unit and re.search(re.escape(unit), text, re.I):
                raise InvalidLLMOutput("Explanation must not restate or change values or units.")
        status_terms = set(re.findall(r"\b(?:normal|low|high|urgent|cannot classify|needs clarification)\b", text, re.I))
        allowed = row["status"].replace("_", " ").casefold()
        if any(term.casefold() != allowed for term in status_terms):
            raise InvalidLLMOutput("Explanation conflicts with a deterministic status.")
    if any(not question.strip() or len(question) > 240 for question in output.doctor_questions):
        raise InvalidLLMOutput("Doctor questions must be short, non-empty strings.")
    if any(any(pattern.search(question) for pattern in _DIAGNOSIS_PATTERNS) for question in output.doctor_questions):
        raise InvalidLLMOutput("Diagnosis wording is not allowed in doctor questions.")
    if any(re.search(r"\d", question) for question in output.doctor_questions):
        raise InvalidLLMOutput("Doctor questions must not add numerical facts.")
    return output

