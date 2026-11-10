"""ReAct 主循环：模型选择动作 → 执行工具 → 观察结果 → 模型调整下一步或结束。

代码只负责：执行工具、记录 trace、执行上限、提交闸门。
“改写检索词还是请求补充”“如何压缩脚本”“重试还是放弃”等决策全部由模型根据工具结果做出。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .config import Limits
from .llm.base import LLMClient, LLMError
from .prompts import SYSTEM_PROMPT, build_user_message
from .schema import Brief
from .tools import TOOL_SCHEMAS, AnswerProvider, FaultPlan, MaterialStore, ToolOutcome, ToolSession
from .trace import TraceRecorder

NUDGE = ("[系统提示] 你没有调用任何工具。请继续通过工具推进；"
         "结束时必须调用 submit_script、report_failure 或 request_user_input 之一。")


@dataclass
class RunResult:
    output: dict[str, Any]
    trace: TraceRecorder
    messages: list[dict[str, Any]]


def _reason_of(arguments: str) -> str:
    try:
        return str(json.loads(arguments or "{}").get("decision_reason") or "")
    except (json.JSONDecodeError, AttributeError):
        return ""


class ScriptAgent:
    def __init__(self, llm: LLMClient, store: MaterialStore, rules: dict[str, Any],
                 limits: Limits | None = None, faults: FaultPlan | None = None,
                 answers: AnswerProvider | None = None):
        self.llm = llm
        self.store = store
        self.rules = rules
        self.limits = limits or Limits()
        self.faults = faults or FaultPlan()
        self.answers = answers or AnswerProvider()

    def run(self, brief: Brief) -> RunResult:
        initial_brief = brief.to_dict()
        session = ToolSession(brief, self.store, self.rules, self.faults, self.answers)
        trace = TraceRecorder()
        trace.add("run_start", llm=self.llm.name, brief=initial_brief, limits=vars(self.limits),
                  faults={k: list(v) for k, v in self.faults.rules.items()},
                  answers=list(self.answers.answers))
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(brief, self.limits, self.rules["duration_policy"])},
        ]

        status: str | None = None
        reason = ""
        tool_calls_used = 0
        steps_used = 0
        for step in range(1, self.limits.max_steps + 1):
            steps_used = step
            try:
                turn = self.llm.chat(messages, TOOL_SCHEMAS)
            except LLMError as exc:
                status, reason = "failed", f"模型调用失败：{exc}"
                trace.add("llm_error", step=step, message=str(exc))
                break
            trace.add("llm_turn", step=step, latency_ms=turn.latency_ms, usage=turn.usage,
                      tool_calls=[c.name for c in turn.tool_calls], text=(turn.content or "")[:200])
            messages.append(turn.message)

            if not turn.tool_calls:
                trace.add("nudge", step=step, text=(turn.content or "")[:120])
                messages.append({"role": "user", "content": NUDGE})
                continue

            for call in turn.tool_calls:
                if tool_calls_used >= self.limits.max_tool_calls:
                    status = "incomplete"
                    reason = f"达到工具调用总上限 {self.limits.max_tool_calls} 次，任务未完成"
                    trace.add("limit", step=step, message=reason)
                    break
                if session.call_counts.get(call.name, 0) >= self.limits.max_calls_per_tool:
                    outcome = ToolOutcome(False, {"ok": False, "error_type": "TOOL_CALL_LIMIT",
                                                  "message": f"{call.name} 已达单工具调用上限 "
                                                             f"{self.limits.max_calls_per_tool} 次，请换一种处理方式或结束"},
                                          f"拒绝：{call.name} 达到单工具调用上限")
                else:
                    outcome = session.execute(call.name, call.arguments)
                tool_calls_used += 1
                args_view = outcome.arg_summary
                if not args_view:
                    raw = _safe_args(call.arguments)
                    args_view = session._arg_summary(call.name, raw) if isinstance(raw, dict) else raw
                trace.add("tool_call", step=step, tool=call.name, args=args_view,
                          decision_reason=_reason_of(call.arguments), ok=outcome.ok,
                          result_summary=outcome.summary)
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(outcome.content, ensure_ascii=False)})
                if outcome.terminal:
                    status = outcome.final_status
                    break
            if status:
                break
        else:
            status = "incomplete"
            reason = f"达到最大决策轮数上限 {self.limits.max_steps}，任务未完成"
            trace.add("limit", step=steps_used, message=reason)

        output = build_output(session, status, reason, self.llm.name, steps_used, tool_calls_used,
                              self.limits, initial_brief)
        trace.add("run_end", status=output["status"], reason=output["status_reason"],
                  steps_used=steps_used, tool_calls_used=tool_calls_used)
        trace.finalize(output["status"])
        return RunResult(output=output, trace=trace, messages=messages)


def _safe_args(arguments: str) -> Any:
    try:
        data = json.loads(arguments or "{}")
        data.pop("decision_reason", None)
        return data
    except json.JSONDecodeError:
        return arguments[:200]


# ----------------------------------------------------------------------
def build_output(session: ToolSession, status: str, reason: str, llm_name: str, steps_used: int,
                 tool_calls_used: int, limits: Limits, initial_brief: dict[str, Any]) -> dict[str, Any]:
    final = session.final or {}
    script = final.get("script")
    version = final.get("script_version")
    duration_check = final.get("duration_check")
    rule_check = final.get("rule_check")

    if script is None and session.scripts:
        # 未完成时附上最后一个版本，供用户继续编辑（明确标注未通过/未检查）
        fp = max(session.versions, key=session.versions.get)
        script, version = session.scripts[fp], f"v{session.versions[fp]}"
        duration_check = session.duration_results.get(fp)
        rule_check = session.rule_results.get(fp)

    per_shot = {s["shot_id"]: s["sec"] for s in (duration_check or {}).get("per_shot", [])}
    shots = []
    for shot in (script or {}).get("shots", []):
        shots.append({"shot_id": shot["shot_id"], "duration_sec": per_shot.get(shot["shot_id"]),
                      "visual": shot["visual"], "narration": shot["narration"], "subtitle": shot["subtitle"],
                      "screen_note": shot["screen_note"], "hold_sec": shot["hold_sec"],
                      "source_ids": shot["source_ids"]})
    used_ids = sorted({i for s in shots for i in s["source_ids"]})
    sources = [session.store.public_view(session.store.by_id[i]) for i in used_ids if i in session.store.by_id]

    if status == "completed":
        status_reason = f"脚本 {version} 已通过时长与规则检查"
    elif status == "needs_input":
        status_reason = "缺少必要信息/素材，已向用户提出补充请求"
    elif status == "failed":
        status_reason = reason or final.get("reason") or "无法满足要求"
    else:
        status_reason = reason

    system_notes = []
    if session.tool_failures:
        system_notes.append(f"工具调用失败 {len(session.tool_failures)} 次：{session.tool_failures}")
    if status != "completed" and script:
        system_notes.append(f"附带的脚本 {version} 未通过全部检查，不可直接发布")
    for w in (rule_check or {}).get("warnings", []):
        system_notes.append(f"规则提示[{w['code']}] {w['where']}：{w['detail']}")
    if llm_name.startswith("mock"):
        system_notes.append("离线 Mock 策略运行：只验证流程与工具链，不代表真实模型的决策效果")

    revisions = []
    for fp, num in sorted(session.versions.items(), key=lambda kv: kv[1]):
        d, r = session.duration_results.get(fp), session.rule_results.get(fp)
        revisions.append({
            "version": f"v{num}",
            "estimated_sec": d["total_sec"] if d else None,
            "duration": d["status"] if d else "未估算",
            "rules": ("通过" if r["passed"] else sorted({v["code"] for v in r["violations"]})) if r else "未检查",
        })

    output: dict[str, Any] = {
        "status": status,
        "status_reason": status_reason,
        "title": (script or {}).get("title"),
        "platform": session.brief.platform,
        "target_duration_sec": session.brief.target_duration_sec,
        "estimated_total_sec": (duration_check or {}).get("total_sec"),
        "script_version": version,
        "shots": shots,
        "sources": sources,
        "checks": {
            "duration": None if not duration_check else {
                k: duration_check[k] for k in ("passed", "status", "total_sec", "allowed_range_sec",
                                               "delta_sec", "speech_rate_cps", "script_version")},
            "rules": None if not rule_check else {
                "passed": rule_check["passed"], "violations": rule_check["violations"],
                "warnings": rule_check["warnings"], "script_version": rule_check["script_version"]},
        },
        "risks": final.get("risks", []),
        "system_notes": system_notes,
        "revision_history": revisions,
        "retrieval": {"queries": session.search_history, "retrieved_ids": sorted(session.retrieved)},
        "brief_initial": initial_brief,
        "brief_final": session.brief.to_dict(),
        "run": {"llm": llm_name, "steps_used": steps_used, "tool_calls_used": tool_calls_used,
                "tool_call_counts": session.call_counts, "limits": vars(limits)},
    }
    if status == "needs_input":
        output["questions"] = final.get("questions", [])
        output["missing"] = final.get("missing", [])
    if status == "failed":
        output["failure"] = {k: final.get(k) for k in ("reason", "failed_checks", "suggestions")}
    if session.user_replies:
        output["user_replies"] = session.user_replies
    return output
