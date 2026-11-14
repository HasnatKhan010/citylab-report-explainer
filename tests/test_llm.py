import asyncio
import json

import httpx
import pytest

from core.service import analyze_patient
from llm.client import CircuitBreaker, LLMClient, Provider
from llm.explain import explain_results, template_explanations
from llm.validator import InvalidLLMOutput, validate_explanation


def _valid_for(analysis):
    return json.dumps({
        "explanations": [
            {"test": row["original_name"], "explanation": "This comparison follows the information listed in the report."}
            for row in analysis["tests"]
        ],
        "doctor_questions": [
            "Could you explain this result?",
            "What information in the report should I review?",
            "What follow-up, if any, do you recommend?",
        ],
    })


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def complete(self, system_prompt, user_prompt, use_cache=True):
        self.calls += 1
        item = self.responses.pop(0)
        return (item, "fake") if item is not None else None


def test_validator_rejects_invalid_json_diagnosis_and_data_changes():
    analysis = analyze_patient("P004")
    with pytest.raises(InvalidLLMOutput):
        validate_explanation("not json", analysis["tests"])
    diagnosis = json.loads(_valid_for(analysis))
    diagnosis["explanations"][0]["explanation"] = "You have a disease."
    with pytest.raises(InvalidLLMOutput):
        validate_explanation(json.dumps(diagnosis), analysis["tests"])
    altered = json.loads(_valid_for(analysis))
    altered["explanations"][0]["status"] = "normal"
    with pytest.raises(InvalidLLMOutput):
        validate_explanation(json.dumps(altered), analysis["tests"])


def test_validator_rejects_changed_status_or_numeric_value():
    analysis = analyze_patient("P004")
    mismatch = json.loads(_valid_for(analysis))
    mismatch["explanations"][0]["explanation"] = "The result is normal."
    with pytest.raises(InvalidLLMOutput):
        validate_explanation(json.dumps(mismatch), analysis["tests"])
    changed_value = json.loads(_valid_for(analysis))
    changed_value["explanations"][0]["explanation"] = "The value is 7."
    with pytest.raises(InvalidLLMOutput):
        validate_explanation(json.dumps(changed_value), analysis["tests"])


def test_invalid_llm_output_retried_once_then_accepted_or_templates():
    analysis = analyze_patient("P004")
    invalid = json.loads(_valid_for(analysis))
    invalid["explanations"][0]["explanation"] = "You have a condition."
    client = FakeClient([json.dumps(invalid), _valid_for(analysis)])
    accepted = asyncio.run(explain_results(analysis, {}, client=client))
    assert accepted["provider"] == "fake"
    assert client.calls == 2

    failing = FakeClient([json.dumps(invalid), json.dumps(invalid)])
    fallback = asyncio.run(explain_results(analysis, {}, client=failing))
    assert fallback["provider"] == "templates"
    assert "see a doctor today" in fallback["explanations"][0]["explanation"].lower()


def test_all_providers_down_uses_english_and_urdu_templates():
    analysis = analyze_patient("P004")
    client = FakeClient([None])
    english = asyncio.run(explain_results(analysis, {}, client=client))
    urdu = template_explanations(analysis, "ur")
    assert english["provider"] == "templates"
    assert "today" in english["explanations"][0]["explanation"]
    assert "ڈاکٹر" in urdu["explanations"][0]["explanation"]


def test_llm_client_cache_breaker_and_retry_after(monkeypatch):
    client = LLMClient(attempts=1)
    provider = Provider("gemini", "key", "model", "")
    monkeypatch.setattr(client, "_providers", lambda: [provider])
    calls = []

    async def fake_request(*args):
        calls.append(1)
        return f"response-{len(calls)}"

    monkeypatch.setattr(client, "_request", fake_request)

    async def run():
        first = await client.complete("s", "u")
        cached = await client.complete("s", "u")
        retry = await client.complete("s", "u", use_cache=False)
        return first, cached, retry

    first, cached, retry = asyncio.run(run())
    assert first[0] == "response-1" and cached[0] == "response-1" and retry[0] == "response-2"
    assert len(calls) == 2

    breaker = CircuitBreaker(threshold=2, cooldown_seconds=10)
    breaker.failure(); breaker.failure()
    assert not breaker.available()
    breaker.success()
    assert breaker.available()

    response = httpx.Response(429, headers={"Retry-After": "3"}, request=httpx.Request("GET", "https://test"))
    error = httpx.HTTPStatusError("limited", request=response.request, response=response)
    assert client._retry_after(error) == 3.0

