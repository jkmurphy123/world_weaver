from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

from world_weaver.llm.base import PromptRequest


@dataclass(slots=True, frozen=True)
class ConnectionStatus:
    provider: str
    model: str
    message: str


class OpenAIProvider:
    """Minimal OpenAI Responses API client using stdlib HTTP."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 120,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI provider requires an API key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def generate_json(self, request_payload: PromptRequest) -> str:
        payload = {
            "model": request_payload.model,
            "instructions": request_payload.system_prompt,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Return valid JSON only.",
                        },
                        {
                            "type": "input_text",
                            "text": request_payload.user_prompt,
                        },
                    ],
                }
            ],
            "text": {"format": {"type": "json_object"}},
        }
        response = self._request_json("POST", "/responses", payload=payload)
        output_text = self._extract_output_text(response)
        if not output_text.strip():
            raise ValueError("OpenAI response did not contain text output")
        return output_text

    def check_connection(self, model: str) -> ConnectionStatus:
        response = self._request_json("GET", f"/models/{parse.quote(model, safe='')}")
        model_id = response.get("id", model)
        return ConnectionStatus(provider="openai", model=str(model_id), message="OpenAI model is reachable")

    def _request_json(self, method: str, path: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url=f"{self._base_url}{path}",
            method=method,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            data=body,
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"OpenAI request failed with HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise ValueError(f"OpenAI request failed: {exc.reason}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI returned non-JSON output") from exc

        if not isinstance(parsed, dict):
            raise ValueError("OpenAI returned an unexpected response shape")
        return parsed

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str):
            return output_text

        chunks: list[str] = []
        output = payload.get("output")
        if not isinstance(output, list):
            return ""

        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "".join(chunks)
