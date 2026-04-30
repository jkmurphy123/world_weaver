from world_weaver.llm.base import LLMProvider, PromptRequest

__all__ = ["LLMProvider", "PromptRequest", "build_provider"]


def __getattr__(name: str):
    if name == "build_provider":
        from world_weaver.llm.factory import build_provider

        return build_provider
    raise AttributeError(name)
