"""Keep the suite hermetic: no test may reach a live provider."""

import pytest


@pytest.fixture(autouse=True)
def no_live_provider(monkeypatch):
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.setenv(name, "")
