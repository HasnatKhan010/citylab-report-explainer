"""Optional language layer with validation retry and deterministic templates."""

from __future__ import annotations

import logging

from llm.client import LLMClient
from llm.prompts import SYSTEM_PROMPT, build_prompt
from llm.validator import InvalidLLMOutput, validate_explanation

logger = logging.getLogger(__name__)
_client = LLMClient()


def _template(row: dict, language: str) -> str:
    status = row["status"]
    if language == "ur":
        templates = {
            "normal": "یہ نتیجہ فائل میں دی گئی حد کے اندر ہے۔ یہ موازنہ تشخیص نہیں ہے۔",
            "low": "یہ نتیجہ فائل میں دی گئی حد سے کم ہے۔ یہ موازنہ تشخیص نہیں ہے۔",
            "high": "یہ نتیجہ فائل میں دی گئی حد سے زیادہ ہے۔ یہ موازنہ تشخیص نہیں ہے۔",
            "urgent": "فائل میں درج اہم حد عبور ہوئی ہے۔ آج ہی ڈاکٹر سے رابطہ کریں۔",
            "cannot_classify": "فائلوں میں اس نتیجے کی درجہ بندی کے لیے کافی معلومات نہیں ہیں۔",
            "needs_clarification": "درجہ بندی سے پہلے مریض کی عمر اور پیدائش کے وقت کی حیاتیاتی جنس درکار ہے۔",
        }
    else:
        templates = {
            "normal": "The result is within the range listed in the files. This comparison is not a diagnosis.",
            "low": "The result is below the range listed in the files. This comparison is not a diagnosis.",
            "high": "The result is above the range listed in the files. This comparison is not a diagnosis.",
            "urgent": "The result crossed a critical limit listed in the files. Please see a doctor today.",
            "cannot_classify": "The files do not contain enough information to classify this result.",
            "needs_clarification": "The patient's age and biological sex at birth are needed before classification.",
        }
    explanation = templates.get(status, templates["cannot_classify"])
    boundary_note = "sheet does not state a boundary rule; hematology convention applied."
    if language != "ur" and boundary_note in row.get("trace", []):
        explanation += " " + boundary_note
    return explanation


def template_explanations(analysis: dict, language: str = "en") -> dict:
    return {
        "explanations": [
            {"test": row["original_name"], "explanation": _template(row, language)}
            for row in analysis["tests"]
        ],
        "doctor_questions": analysis["doctor_questions"] if language == "en" else [
            "کیا آپ اس نتیجے کی وضاحت کر سکتے ہیں؟",
            "کیا آپ بتا سکتے ہیں کہ رپورٹ میں کون سی معلومات دی گئی ہیں؟",
            "کیا اس نتیجے کے لیے کسی اگلے قدم کی ضرورت ہے؟",
        ] if analysis["doctor_questions"] else [],
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

