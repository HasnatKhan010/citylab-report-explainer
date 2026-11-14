import asyncio

import httpx

from app.main import app
from core.classify import BOUNDARY_ASSUMPTION
from adapters.scorer import analyze as scorer_analyze, ask as scorer_ask


def request(method, path, **kwargs):
    async def make_request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(make_request())


def test_health_patient_list_and_active_patient_analyze():
    health = request("GET", "/health")
    assert health.status_code == 200
    assert health.json()["patients_loaded"] == 14
    patients = request("GET", "/patients").json()
    assert len(patients) == 14
    assert patients[0] == {"patient_id": "P001"}
    assert "patient_name" not in patients[1]

    response = request("POST", "/analyze", json={"patient_id": "P002", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    assert data["tests"][0]["status"] == "normal"
    assert BOUNDARY_ASSUMPTION in data["tests"][0]["explanation"]
    assert data["explanation_provider"] == "templates"


def test_api_refuses_other_patient_and_hides_internal_errors():
    refusal = request("POST", "/ask", json={"patient_id": "P001", "question": "What is P002's result?"})
    assert refusal.status_code == 200
    assert refusal.json()["refused"]
    assert refusal.json()["citations"][0]["source_file"] == "1_lab_safety_rules.md"

    missing = request("POST", "/analyze", json={"patient_id": "P999"})
    assert missing.status_code == 404
    assert "Traceback" not in missing.text
    invalid = request("POST", "/ask", json={"patient_id": "P001", "question": " ", "unused": 1})
    assert invalid.status_code == 422


def test_scorer_adapter_is_small_and_html_is_served():
    assert scorer_analyze({"patient_id": "P002"})["patient_id"] == "P002"
    assert scorer_ask({"patient_id": "P001", "question": "What is my report?"})["patient_id"] == "P001"
    assert "اردو" in request("GET", "/").text


def test_urdu_language_returns_urdu_explanation():
    response = request("POST", "/analyze", json={"patient_id": "P004", "language": "ur"})
    assert response.status_code == 200
    assert "ڈاکٹر" in response.json()["tests"][0]["explanation"]



PASTED_REPORT = """# CITYLAB DIAGNOSTICS - URINALYSIS AND CHEMISTRY
* **Patient Full Name**: Pasted Person
* **Recorded Age**: 30
* **Biological Sex**: Male

## SECTION III: ANALYTICAL RESULTS
- **FBS**: 7.5 mmol/L
- **Hb**: 150 g/L
* pH Level -> 9.0
"""


def test_pasted_report_is_classified_against_the_same_reference_files():
    response = request("POST", "/analyze-text", json={"report_text": PASTED_REPORT})
    assert response.status_code == 200
    body = response.json()
    assert body["source_file"] == "pasted report"
    assert body["patient_name"] == "Pasted Person"
    by_name = {row["original_name"]: row for row in body["tests"]}
    assert by_name["FBS"]["canonical_name"] == "Fasting Blood Sugar"
    assert by_name["FBS"]["status"] == "high"
    assert by_name["FBS"]["conversion_shown"]["working"] == "7.5 mmol/L x 18.0182 = 135.14 mg/dL"
    assert by_name["Hb"]["status"] == "normal"
    assert by_name["pH Level"]["canonical_name"] == "Urine pH"
    assert by_name["pH Level"]["status"] == "high"
    assert 3 <= len(body["doctor_questions"]) <= 5


def test_pasted_report_without_readable_results_is_rejected():
    response = request("POST", "/analyze-text", json={"report_text": "no results here"})
    assert response.status_code == 422
    assert "test name and a value" in response.json()["detail"]


def test_pasted_report_still_refuses_to_guess_missing_demographics():
    text = PASTED_REPORT.replace("* **Biological Sex**: Male", "* **Biological Sex**: [NOT PROVIDED]")
    body = request("POST", "/analyze-text", json={"report_text": text}).json()
    assert body["needs_clarification"] is True
    assert all(row["status"] == "needs_clarification" for row in body["tests"])


def test_scorer_adapter_accepts_pasted_report_text():
    from adapters.scorer import analyze_text

    result = analyze_text({"report_text": PASTED_REPORT})
    assert result["tests"][0]["canonical_name"] == "Fasting Blood Sugar"
