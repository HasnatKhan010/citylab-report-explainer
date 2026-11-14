"""Optional language layer with validation retry and deterministic templates."""

from __future__ import annotations

import logging

from core.classify import BOUNDARY_ASSUMPTION
from llm.client import LLMClient
from llm.prompts import SYSTEM_PROMPT, build_prompt
from llm.validator import InvalidLLMOutput, validate_explanation

logger = logging.getLogger(__name__)
_client = LLMClient()


def _template(row: dict, language: str) -> str:
    """Fallback wording: the comparison itself. The plain-language fields stand apart."""
    if language == "ur":
        templates = {
            "normal": "یہ نتیجہ فائل میں دی گئی حد کے اندر ہے۔ یہ موازنہ تشخیص نہیں ہے۔",
            "low": "یہ نتیجہ فائل میں دی گئی حد سے کم ہے۔ یہ موازنہ تشخیص نہیں ہے۔",
            "high": "یہ نتیجہ فائل میں دی گئی حد سے زیادہ ہے۔ یہ موازنہ تشخیص نہیں ہے۔",
            "urgent": "فائل میں درج اہم حد عبور ہوئی ہے۔ آج ہی ڈاکٹر سے رابطہ کریں۔",
            "cannot_classify": "فائلوں میں اس نتیجے کی درجہ بندی کے لیے کافی معلومات نہیں ہیں۔",
            "needs_clarification": "درجہ بندی سے پہلے مریض کی عمر اور پیدائش کے وقت کی حیاتیاتی جنس درکار ہے۔",
        }
        explanation = templates.get(row["status"], templates["cannot_classify"])
    else:
        # The deterministic layer already names the source file it compared against.
        explanation = row["explanation"]
    boundary_note = BOUNDARY_ASSUMPTION
    if language != "ur" and boundary_note in row.get("trace", []) and boundary_note not in explanation:
        explanation += " " + boundary_note
    return explanation


def template_explanations(analysis: dict, language: str = "en") -> dict:
    return {
        "explanations": [
            {"test": row["original_name"], "explanation": _template(row, language)}
            for row in analysis["tests"]
        ],
        "doctor_questions": analysis["doctor_questions"],
        "provider": "templates",
    }


async def explain_results(analysis: dict, glossary: dict[str, str], language: str = "en", client: LLMClient | None = None) -> dict:
    client = client or _client
    fallback = template_explanations(analysis, language)
    if not analysis["tests"]:
        return fallback
    prompt = build_prompt(analysis["tests"], glossary, language)
    for attempt in range(2):
        generated = await client.complete(SYSTEM_PROMPT, prompt, use_cache=attempt == 0)
        if generated is None:
            return fallback
        raw, provider = generated
        try:
            output = validate_explanation(raw, analysis["tests"])
            return {
                "explanations": [item.model_dump() for item in output.explanations],
                "doctor_questions": output.doctor_questions,
                "provider": provider,
            }
        except InvalidLLMOutput as exc:
            logger.warning("Rejected LLM wording (attempt %d): %s", attempt + 1, exc)
            if attempt == 1:
                return fallback
    return fallback

