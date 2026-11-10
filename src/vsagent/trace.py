"""运行记录：每一步的动作、参数摘要、返回摘要、决策依据、后续动作。

只记录模型在 decision_reason 中给出的简短依据，不记录模型内部思维过程。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def _cell(value: Any, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = text.replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


class TraceRecorder:
    def __init__(self):
        self.events: list[dict[str, Any]] = []
        self._t0 = time.perf_counter()

    def _ms(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000)

    def add(self, event_type: str, **data: Any) -> dict[str, Any]:
        event = {"type": event_type, "t_ms": self._ms(), **data}
        self.events.append(event)
        return event

    def tool_calls(self) -> list[dict[str, Any]]:
        return [e for e in self.events if e["type"] == "tool_call"]

    def finalize(self, status: str) -> None:
        """回填每次工具调用之后模型实际采取的“后续动作”。"""
        calls = self.tool_calls()
        for current, nxt in zip(calls, calls[1:] + [None]):
            current["next_action"] = nxt["tool"] if nxt else f"结束（{status}）"

    # ---- 输出 ----
    def write_jsonl(self, path: Path) -> None:
        with Path(path).open("w", encoding="utf-8") as fh:
            for e in self.events:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    def to_markdown(self, title: str = "运行记录") -> str:
        start = next((e for e in self.events if e["type"] == "run_start"), {})
        end = next((e for e in self.events if e["type"] == "run_end"), {})
        lines = [f"# {title}", ""]
        if start:
            lines += [
                f"- 模型：`{start.get('llm')}`",
                f"- 执行上限：{start.get('limits')}",
                f"- 故障注入：{start.get('faults') or '无'}；预置用户回答：{start.get('answers') or '无'}",
                "",
            ]
        lines += ["| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |",
                  "|---|---|---|---|---|---|"]
        for e in self.events:
            if e["type"] == "tool_call":
                ok = "" if e["ok"] else "❌ "
                lines.append(f"| {e['step']} | `{e['tool']}` | {_cell(e['args'])} | {ok}{_cell(e['result_summary'])} "
                             f"| {_cell(e.get('decision_reason') or '')} | {_cell(e.get('next_action', ''))} |")
            elif e["type"] == "nudge":
                lines.append(f"| {e['step']} | （无工具调用） | - | 系统提示继续调用工具 | {_cell(e.get('text') or '')} | - |")
            elif e["type"] == "limit":
                lines.append(f"| {e['step']} | （上限） | - | {_cell(e['message'])} | - | 结束 |")
        if end:
            lines += ["", f"**结束状态：`{end.get('status')}`** — {end.get('reason')}",
                      f"（决策轮数 {end.get('steps_used')}，工具调用 {end.get('tool_calls_used')} 次）"]
        return "\n".join(lines) + "\n"
