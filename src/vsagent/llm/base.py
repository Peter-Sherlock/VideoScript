"""模型接口抽象：Agent 只依赖 chat(messages, tools) -> AssistantTurn。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # 模型给出的原始 JSON 字符串


@dataclass
class AssistantTurn:
    content: str | None
    tool_calls: list[ToolCall]
    message: dict[str, Any]                 # 原样追加到对话历史的 assistant 消息
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0


class LLMError(RuntimeError):
    """模型调用失败（网络、鉴权、限流等）。"""


class LLMClient(Protocol):
    name: str

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn: ...
