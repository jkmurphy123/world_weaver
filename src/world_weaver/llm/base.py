from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class PromptRequest:
    system_prompt: str
    user_prompt: str
    model: str


class LLMProvider(Protocol):
    def generate_json(self, request: PromptRequest) -> str:
        """Return a JSON string response for the supplied prompt."""
