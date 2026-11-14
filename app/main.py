"""FastAPI endpoints plus a small single-page report viewer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from core.ingest import load_corpus
from core.service import analyze_patient, answer_question
from llm.explain import explain_results

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"
CORPUS = load_corpus()

app = FastAPI(title="Medical Lab Report Explainer", version="0.1.0")


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str = Field(min_length=1, max_length=32)
    language: Literal["en", "ur"] = "en"


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str = Field(min_length=1, max_length=32)
    question: str = Field(min_length=1, max_length=1000)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "patients_loaded": len(CORPUS.patients), "llm_optional": True}


@app.get("/patients")
def patients():
    return [{"patient_id": p.patient_id} for p in sorted(CORPUS.patients.values(), key=lambda p: p.patient_id)]


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        result = analyze_patient(request.patient_id, CORPUS, request.language)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Patient ID was not found in the reports.") from exc
    try:
        wording = await explain_results(result, CORPUS.glossary, request.language)
    except Exception as exc:
        # The classification has already succeeded. Wording failures never discard it.
        logger.warning("Explanation layer unavailable: %s", type(exc).__name__)
        from llm.explain import template_explanations

        wording = template_explanations(result, request.language)
    by_name = {item["test"]: item["explanation"] for item in wording["explanations"]}
    for row in result["tests"]:
        row["explanation"] = by_name.get(row["original_name"], row["explanation"])
        # Preserve the exact boundary assumption text required by the reference rule.
        note = "sheet does not state a boundary rule; hematology convention applied."
        if note in row["trace"] and note not in row["explanation"]:
            row["explanation"] += " " + note
    result["doctor_questions"] = wording["doctor_questions"]
    result["explanation_provider"] = wording["provider"]
    return result


@app.post("/ask")
def ask(request: AskRequest):
    try:
        return answer_question(request.patient_id, request.question, CORPUS)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Patient ID was not found in the reports.") from exc

