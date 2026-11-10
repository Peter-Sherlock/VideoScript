from __future__ import annotations

from ..config import LLMSettings
from .base import AssistantTurn, LLMClient, LLMError, ToolCall
from .mock import MockPolicy


def create_llm(settings: LLMSettings) -> LLMClient:
    """按配置创建模型客户端：deepseek（默认）/ openai_compat / mock。"""
    if settings.provider == "mock":
        return MockPolicy()
    if settings.provider in ("deepseek", "openai_compat"):
        from .openai_compat import OpenAICompatClient

        return OpenAICompatClient(
            base_url=settings.base_url, api_key=settings.api_key or "", model=settings.model,
            thinking=settings.thinking, temperature=settings.temperature,
            timeout_sec=settings.timeout_sec, is_deepseek=settings.provider == "deepseek",
        )
    raise LLMError(f"未知 LLM_PROVIDER：{settings.provider}（可选 deepseek / openai_compat / mock）")


__all__ = ["AssistantTurn", "LLMClient", "LLMError", "ToolCall", "MockPolicy", "create_llm"]
