"""Command-line adapter for local demonstrations."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from dotenv import load_dotenv

from core.ingest import load_corpus
from core.service import analyze_patient, answer_question
from llm.explain import explain_results


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="citylab", description="Explain a CityLab report using organizer files only.")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="Analyze one active patient report")
    analyze.add_argument("patient_id")
    analyze.add_argument("--language", choices=("en", "ur"), default="en")
    ask = sub.add_parser("ask", help="Ask a files-only follow-up question")
    ask.add_argument("patient_id")
    ask.add_argument("question")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        if args.command == "analyze":
            corpus = load_corpus()
            analysis = analyze_patient(args.patient_id, corpus)
            wording = asyncio.run(explain_results(analysis, corpus.glossary, args.language))
            for row, explanation in zip(analysis["tests"], wording["explanations"]):
                row["explanation"] = explanation["explanation"]
            analysis["doctor_questions"] = wording["doctor_questions"]
            analysis["explanation_provider"] = wording["provider"]
            result = analysis
        else:
            result = answer_question(args.patient_id, args.question)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except KeyError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

