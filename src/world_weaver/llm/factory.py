from __future__ import annotations

from world_weaver.config import Settings
from world_weaver.llm.base import LLMProvider
from world_weaver.llm.mock_provider import MockLLMProvider
from world_weaver.llm.openai_provider import OpenAIProvider


def build_provider(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "mock":
        return MockLLMProvider()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI provider requires NEWSROOM_OPENAI_API_KEY or OPENAI_API_KEY to be set."
            )
        return OpenAIProvider(api_key=settings.openai_api_key)
    msg = (
        f"Unsupported LLM provider '{settings.llm_provider}'. "
        "Supported providers are: mock, openai."
    )
    raise ValueError(msg)
