import json
from typing import Any

import pytest

from vsagent.config import MATERIALS_PATH, RULES_PATH
from vsagent.llm.base import AssistantTurn, ToolCall
from vsagent.schema import Brief
from vsagent.tools import MaterialStore


@pytest.fixture(scope="session")
def store() -> MaterialStore:
    return MaterialStore(MATERIALS_PATH)


@pytest.fixture(scope="session")
def rules() -> dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def m2_brief() -> Brief:
    return Brief.from_dict({"topic": "vlog 收音", "product": "帧跃 M2 无线麦克风", "audience": "vlog 新手",
                            "platform": "抖音", "target_duration_sec": 30, "style": "轻松种草"})


@pytest.fixture
def editor_brief() -> Brief:
    return Brief.from_dict({"topic": "自动字幕", "product": "帧跃剪辑 App", "platform": "视频号",
                            "target_duration_sec": 30, "style": "干货讲解"})


def shot(narration: str, source_ids=(), visual: str = "画面", **extra) -> dict[str, Any]:
    return {"shot_id": 0, "visual": visual, "narration": narration, "source_ids": list(source_ids), **extra}


class ScriptedLLM:
    """按预设顺序返回工具调用的假模型；可传入函数，根据上一条工具结果动态决定。"""

    name = "scripted/test"

    def __init__(self, steps):
        self.steps = list(steps)
        self.seen_results: list[dict[str, Any]] = []
        self.n = 0

    def chat(self, messages, tools):
        if messages[-1].get("role") == "tool":
            self.seen_results.append(json.loads(messages[-1]["content"]))
        step = self.steps.pop(0) if self.steps else ("report_failure", {"reason": "脚本用完", "suggestions": []})
        if callable(step):
            step = step(self.seen_results[-1] if self.seen_results else None)
        if step is None:  # 模拟模型只回复文字、不调用工具
            msg = {"role": "assistant", "content": "我想先说点什么"}
            return AssistantTurn(content="我想先说点什么", tool_calls=[], message=msg)
        calls = step if isinstance(step, list) else [step]
        tool_calls = []
        for name, args in calls:
            self.n += 1
            tool_calls.append(ToolCall(id=f"c{self.n}", name=name,
                                       arguments=args if isinstance(args, str) else
                                       json.dumps({**args, "decision_reason": "test"}, ensure_ascii=False)))
        msg = {"role": "assistant", "content": "",
               "tool_calls": [{"id": c.id, "type": "function",
                               "function": {"name": c.name, "arguments": c.arguments}} for c in tool_calls]}
        return AssistantTurn(content="", tool_calls=tool_calls, message=msg)
