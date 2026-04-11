from __future__ import annotations

from world_weaver.config import Settings
from world_weaver.llm.base import LLMProvider
from world_weaver.llm.mock_provider import MockLLMProvider


def build_provider(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "mock":
        return MockLLMProvider()
    msg = (
        f"Unsupported LLM provider '{settings.llm_provider}'. "
        "Set NEWSROOM_LLM_PROVIDER=mock for local development."
    )
    raise ValueError(msg)
