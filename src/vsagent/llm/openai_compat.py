"""OpenAI 兼容接口（默认对接 DeepSeek：https://api.deepseek.com，模型 deepseek-flash）。

要点：
- base_url / api_key 显式传入，避免被系统里的 OPENAI_BASE_URL 等变量“串台”。
- DeepSeek 默认开启思考模式；本项目默认 LLM_THINKING=disabled（更快、更省，且 temperature 生效）。
  若开启思考模式，DeepSeek 要求把 reasoning_content 原样回传，这里会保留在对话历史中，
  但不写入 trace（题目不要求提交模型内部思维）。
"""
from __future__ import annotations

import time
from typing import Any

from .base import AssistantTurn, LLMError, ToolCall


class OpenAICompatClient:
    def __init__(self, base_url: str, api_key: str, model: str, *, thinking: str = "disabled",
                 temperature: float = 0.3, timeout_sec: float = 90.0, is_deepseek: bool = True):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMError("缺少 openai 依赖，请先 pip install -r requirements.txt") from exc
        if not api_key:
            raise LLMError("未配置 API Key：请在 .env 中设置 DEEPSEEK_API_KEY（或改用 --llm mock 离线运行）")
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_sec, max_retries=2)
        self.model = model
        self.thinking = thinking
        self.temperature = temperature
        self.is_deepseek = is_deepseek
        self.name = f"{'deepseek' if is_deepseek else 'openai_compat'}/{model}"

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn:
        from openai import APIConnectionError, APIStatusError, APITimeoutError

        kwargs: dict[str, Any] = {"model": self.model, "messages": messages, "tools": tools,
                                  "tool_choice": "auto", "max_tokens": 8000}
        if self.is_deepseek:
            kwargs["extra_body"] = {"thinking": {"type": self.thinking}}
        if not (self.is_deepseek and self.thinking == "enabled"):
            kwargs["temperature"] = self.temperature
        start = time.perf_counter()
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except APITimeoutError as exc:
            raise LLMError(f"模型请求超时：{exc}") from exc
        except APIStatusError as exc:
            raise LLMError(f"模型接口返回 HTTP {exc.status_code}：{exc.message}") from exc
        except APIConnectionError as exc:
            raise LLMError(f"无法连接模型接口：{exc}") from exc
        latency = int((time.perf_counter() - start) * 1000)

        msg = resp.choices[0].message
        calls = [ToolCall(id=c.id, name=c.function.name, arguments=c.function.arguments or "{}")
                 for c in (msg.tool_calls or [])]
        history_msg: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if calls:
            history_msg["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in calls
            ]
        reasoning = getattr(msg, "reasoning_content", None) or (msg.model_extra or {}).get("reasoning_content")
        if reasoning:
            history_msg["reasoning_content"] = reasoning
        usage = {}
        if resp.usage:
            usage = {"prompt_tokens": resp.usage.prompt_tokens, "completion_tokens": resp.usage.completion_tokens}
        return AssistantTurn(content=msg.content, tool_calls=calls, message=history_msg,
                             usage=usage, latency_ms=latency)
