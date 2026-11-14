"""Minimal scorer adapter, intentionally isolated from the deterministic core."""

from __future__ import annotations

from typing import Any

from core.service import analyze_patient, answer_question


def analyze(payload: dict[str, Any]) -> dict:
    patient_id = payload.get("patient_id")
    if not isinstance(patient_id, str) or not patient_id.strip():
        raise ValueError("patient_id is required")
    return analyze_patient(patient_id)


def ask(payload: dict[str, Any]) -> dict:
    patient_id = payload.get("patient_id")
    question = payload.get("question")
    if not isinstance(patient_id, str) or not patient_id.strip():
        raise ValueError("patient_id is required")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question is required")
    return answer_question(patient_id, question)

