import json
from urllib import request

import pytest

from world_weaver.config import Settings
from world_weaver.llm.base import PromptRequest
from world_weaver.llm.factory import build_provider
from world_weaver.llm.openai_provider import OpenAIProvider


class _FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_openai_provider_generate_json_extracts_response_text(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _fake_urlopen(req: request.Request, timeout: int = 30) -> _FakeHTTPResponse:
        captured["url"] = req.full_url
        captured["auth"] = req.headers["Authorization"]
        captured["body"] = req.data.decode("utf-8")
        return _FakeHTTPResponse(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"date":"2026-04-11","stories":[]}',
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr(request, "urlopen", _fake_urlopen)
    provider = OpenAIProvider(api_key="test-key")

    payload = provider.generate_json(
        PromptRequest(system_prompt="Return JSON", user_prompt='{"hello":"world"}', model="gpt-4.1")
    )

    assert payload == '{"date":"2026-04-11","stories":[]}'
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["auth"] == "Bearer test-key"
    request_body = json.loads(captured["body"])
    assert request_body["model"] == "gpt-4.1"
    assert request_body["instructions"] == "Return JSON"
    assert request_body["input"] == [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Return valid JSON only."},
                {"type": "input_text", "text": '{"hello":"world"}'},
            ],
        }
    ]


def test_openai_provider_check_connection_calls_model_endpoint(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _fake_urlopen(req: request.Request, timeout: int = 30) -> _FakeHTTPResponse:
        captured["url"] = req.full_url
        return _FakeHTTPResponse({"id": "gpt-4.1", "object": "model"})

    monkeypatch.setattr(request, "urlopen", _fake_urlopen)
    provider = OpenAIProvider(api_key="test-key")

    status = provider.check_connection("gpt-4.1")

    assert status.provider == "openai"
    assert status.model == "gpt-4.1"
    assert captured["url"] == "https://api.openai.com/v1/models/gpt-4.1"


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenAIProvider(api_key="")


def test_build_provider_passes_configured_openai_timeout() -> None:
    provider = build_provider(
        Settings(
            llm_provider="openai",
            llm_model="gpt-4.1",
            openai_api_key="test-key",
            openai_timeout_seconds=300,
        )
    )

    assert isinstance(provider, OpenAIProvider)
    assert provider._timeout_seconds == 300
