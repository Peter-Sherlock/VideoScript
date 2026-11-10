"""工具注册表：工具 schema、会话状态、故障注入、提交闸门。

模型只能通过这里的工具与外部交互。几个关键约束：
- 素材必须先被检索到，才能被脚本引用（retrieved）。
- 时长/规则检查结果按“脚本指纹”记录；submit_script 只接受【同一版本】两项检查都通过的脚本。
- update_brief 只能填补缺失字段，且必须在用户补充信息之后，模型不能自己改目标时长来“通过”检查。
- 故障注入只影响工具返回值（返回结构化错误），是否重试/放弃由模型决定，代码不自动重试。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ..schema import Brief, ScriptError, normalize_script, script_fingerprint
from . import duration as duration_tool
from .materials import MaterialStore
from .rules import RuleChecker

TERMINAL_TOOLS = {"submit_script", "report_failure", "request_user_input"}

_REASON = {
    "type": "string",
    "description": "一句话说明为什么选择这个动作（依据上一步观察到的结果），不超过 60 字",
}

_SCRIPT_SCHEMA = {
    "type": "object",
    "description": "完整脚本（每次修改后都要传完整版本）",
    "properties": {
        "title": {"type": "string", "description": "视频标题"},
        "shots": {
            "type": "array",
            "description": "分镜列表，按播放顺序",
            "items": {
                "type": "object",
                "properties": {
                    "shot_id": {"type": "integer"},
                    "visual": {"type": "string", "description": "画面/镜头描述"},
                    "narration": {"type": "string", "description": "口播旁白（计入时长）"},
                    "subtitle": {"type": "string", "description": "屏幕字幕，通常为旁白的精简版"},
                    "screen_note": {"type": "string", "description": "角标/免责说明小字（不计入口播时长）"},
                    "hold_sec": {"type": "number", "description": "无旁白展示镜头的停留秒数，可选"},
                    "source_ids": {"type": "array", "items": {"type": "string"},
                                   "description": "本分镜事实所依据的素材 ID；纯氛围/提问镜头可为空数组"},
                },
                "required": ["shot_id", "visual", "narration", "source_ids"],
            },
        },
    },
    "required": ["title", "shots"],
}


def _fn(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    props = dict(properties)
    props["decision_reason"] = _REASON
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": props, "required": [*required, "decision_reason"]},
        },
    }


TOOL_SCHEMAS = [
    _fn("search_materials",
        "在产品素材库中检索事实素材。product 为严格过滤（需与产品名/别名一致）；无结果时会返回现有产品列表作为提示。",
        {
            "query": {"type": "string", "description": "检索词，如产品名 + 卖点关键词"},
            "product": {"type": "string", "description": "可选，产品名；不确定时可不填"},
            "material_types": {"type": "array", "items": {"type": "string",
                               "enum": ["feature", "spec", "effect_data", "price", "brand"]},
                               "description": "可选，按素材类型过滤"},
        }, ["query"]),
    _fn("estimate_duration",
        "估算脚本口播时长：返回逐镜秒数、总时长、是否落在目标区间，以及超时/不足时的修改建议。",
        {"script": _SCRIPT_SCHEMA}, ["script"]),
    _fn("check_rules",
        "检查脚本是否符合事实可追溯、品牌、平台与用户必含要点规则；返回违规项和修改建议。",
        {"script": _SCRIPT_SCHEMA}, ["script"]),
    _fn("request_user_input",
        "向用户请求补充信息（缺关键字段、素材库无可用素材等）。调用后本轮任务将暂停等待用户。",
        {
            "questions": {"type": "array", "items": {"type": "string"}, "description": "要问用户的具体问题"},
            "missing": {"type": "array", "items": {"type": "string"}, "description": "缺少的字段或材料"},
        }, ["questions"]),
    _fn("update_brief",
        "把用户补充的信息写入任务简报。只能填写原本缺失的字段，且必须基于用户的回答。",
        {
            "platform": {"type": "string"},
            "target_duration_sec": {"type": "number"},
            "topic": {"type": "string"},
            "product": {"type": "string"},
            "audience": {"type": "string"},
            "style": {"type": "string"},
        }, []),
    _fn("submit_script",
        "提交最终脚本。只有当【这一版】脚本已通过 estimate_duration 与 check_rules 时才会被接受。",
        {
            "script": _SCRIPT_SCHEMA,
            "risks": {"type": "array", "items": {"type": "string"},
                      "description": "仍存在的风险/假设，例如“受众未提供，按 vlog 新手假设”"},
        }, ["script", "risks"]),
    _fn("report_failure",
        "明确报告无法满足要求（如时长与必含要点冲突、关键工具持续失败），并给出原因与建议。",
        {
            "reason": {"type": "string", "description": "无法完成的原因"},
            "failed_checks": {"type": "array", "items": {"type": "string"}},
            "suggestions": {"type": "array", "items": {"type": "string"}, "description": "给用户的可行调整建议"},
            "best_script": {**_SCRIPT_SCHEMA, "description": "可选，目前最接近要求的草稿"},
        }, ["reason", "suggestions"]),
]


# ----------------------------------------------------------------------
@dataclass
class FaultPlan:
    """故障注入：tool -> (mode, 次数)。transient: 前 n 次失败；permanent: 一直失败。"""

    rules: dict[str, tuple[str, int]] = field(default_factory=dict)

    @classmethod
    def parse(cls, specs: list[str] | None) -> "FaultPlan":
        plan = cls()
        for spec in specs or []:
            parts = spec.split(":")
            tool, mode = parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "transient")
            count = int(parts[2]) if len(parts) > 2 else 1
            if mode not in ("transient", "permanent"):
                raise ValueError(f"未知故障模式 {mode}（可选 transient / permanent）")
            plan.rules[tool] = (mode, count)
        return plan

    def error_for(self, tool: str, call_index: int) -> dict[str, Any] | None:
        if tool not in self.rules:
            return None
        mode, count = self.rules[tool]
        if mode == "permanent":
            return {"error_type": "SERVICE_UNAVAILABLE", "retryable": True,
                    "message": f"{tool} 服务暂不可用（HTTP 503，注入故障）"}
        if call_index <= count:
            return {"error_type": "TIMEOUT", "retryable": True,
                    "message": f"{tool} 调用超时（10s，注入故障）"}
        return None


@dataclass
class ToolOutcome:
    ok: bool
    content: dict[str, Any]       # 返回给模型的内容
    summary: str                  # 写入 trace 的返回摘要
    terminal: bool = False        # 是否结束本次运行
    final_status: str | None = None
    arg_summary: dict[str, Any] = field(default_factory=dict)


class AnswerProvider:
    """request_user_input 的应答来源：脚本化答案（--answers）或交互式输入（--interactive）。"""

    def __init__(self, answers: list[str] | None = None, interactive: bool = False,
                 ask: Callable[[str], str] = input):
        self.answers = list(answers or [])
        self.interactive = interactive
        self.ask = ask

    def get(self, questions: list[str]) -> str | None:
        if self.answers:
            return self.answers.pop(0)
        if self.interactive:
            print("\n[Agent 需要补充信息]")
            for q in questions:
                print(" -", q)
            reply = self.ask("你的回答（直接回车表示不补充）：").strip()
            return reply or None
        return None


# ----------------------------------------------------------------------
class ToolSession:
    def __init__(self, brief: Brief, store: MaterialStore, rules: dict[str, Any],
                 faults: FaultPlan | None = None, answers: AnswerProvider | None = None):
        self.brief = brief
        self.store = store
        self.rules = rules
        self.checker = RuleChecker(rules, store.brand)
        self.faults = faults or FaultPlan()
        self.answers = answers or AnswerProvider()
        self.retrieved: dict[str, dict[str, Any]] = {}
        self.call_counts: dict[str, int] = {}
        self.versions: dict[str, int] = {}             # 指纹 -> 版本号
        self.scripts: dict[str, dict[str, Any]] = {}   # 指纹 -> 脚本
        self.duration_results: dict[str, dict[str, Any]] = {}
        self.rule_results: dict[str, dict[str, Any]] = {}
        self.user_replies: list[str] = []
        self.tool_failures: list[str] = []
        self.search_history: list[dict[str, Any]] = []
        self.final: dict[str, Any] | None = None

    # ---- helpers ----
    def _version(self, script: dict[str, Any]) -> tuple[str, str]:
        fp = script_fingerprint(script)
        if fp not in self.versions:
            self.versions[fp] = len(self.versions) + 1
            self.scripts[fp] = script
        return fp, f"v{self.versions[fp]}"

    def brief_product_id(self) -> str | None:
        p = self.store.resolve_product(self.brief.product) if self.brief.product else None
        return p["product_id"] if p else None

    @staticmethod
    def _script_summary(script: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": script["title"],
            "shots": len(script["shots"]),
            "narration_chars": sum(len(s["narration"]) for s in script["shots"]),
            "source_ids": sorted({i for s in script["shots"] for i in s["source_ids"]}),
        }

    # ---- dispatch ----
    def execute(self, name: str, raw_args: str | dict[str, Any]) -> ToolOutcome:
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args or "{}")
            except json.JSONDecodeError as exc:
                return ToolOutcome(False, {"ok": False, "error_type": "INVALID_ARGUMENTS",
                                           "message": f"参数不是合法 JSON：{exc}"}, "参数 JSON 解析失败")
        else:
            args = dict(raw_args)
        args.pop("decision_reason", None)
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return ToolOutcome(False, {"ok": False, "error_type": "UNKNOWN_TOOL", "message": f"没有工具 {name}"},
                               f"未知工具 {name}")
        self.call_counts[name] = self.call_counts.get(name, 0) + 1
        fault = self.faults.error_for(name, self.call_counts[name])
        if fault:
            self.tool_failures.append(f"{name}: {fault['error_type']}")
            return ToolOutcome(False, {"ok": False, **fault}, f"失败：{fault['error_type']}（{fault['message']}）",
                               arg_summary=self._arg_summary(name, args))
        try:
            return handler(args)
        except ScriptError as exc:
            return ToolOutcome(False, {"ok": False, "error_type": "INVALID_SCRIPT", "message": str(exc)},
                               f"脚本结构错误：{exc}", arg_summary=self._arg_summary(name, args))
        except (ValueError, TypeError, KeyError) as exc:
            return ToolOutcome(False, {"ok": False, "error_type": "INVALID_ARGUMENTS", "message": str(exc)},
                               f"参数错误：{exc}", arg_summary=self._arg_summary(name, args))

    def _arg_summary(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for k, v in args.items():
            if k in ("script", "best_script") and v:
                try:
                    s = normalize_script(v)
                    fp = script_fingerprint(s)
                    out[k] = {**self._script_summary(s),
                              "version": f"v{self.versions[fp]}" if fp in self.versions else "未登记(工具未执行)"}
                except ScriptError:
                    out[k] = "<结构无效>"
            else:
                out[k] = v
        return out

    # ---- tools ----
    def _tool_search_materials(self, args):
        query, product = args.get("query", ""), args.get("product")
        result = self.store.search(query, product=product, material_types=args.get("material_types"))
        for item in result["items"]:
            self.retrieved[item["id"]] = self.store.by_id[item["id"]]
        self.search_history.append({"query": query, "product": product, "count": result["count"]})
        ids = [i["id"] for i in result["items"]]
        summary = f"命中 {result['count']} 条 {ids}" if ids else f"命中 0 条；{result.get('hint', '')}"
        return ToolOutcome(True, {"ok": True, **result}, summary, arg_summary=dict(args))

    def _duplicate(self, tool: str, script: dict[str, Any], fp: str, ver: str,
                   done: dict[str, Any]) -> ToolOutcome | None:
        """真实运行发现：模型会声称“已修改”却重复提交同一版本。不再重算，直接指出，由模型决定改稿还是放弃。"""
        if fp not in done:
            return None
        prev = done[fp]
        keys = ("passed", "status", "total_sec", "allowed_range_sec", "recommended_sec", "violation_count")
        message = (f"本次提交的脚本与已检查过的 {ver} 内容完全相同（上次 {tool} 结果："
                   f"{'通过' if prev['passed'] else '未通过'}），没有任何实际修改，未重新计算。"
                   "如果要继续修改，请在 script 参数中实际改动旁白/分镜文字；"
                   "如果判断已无法在约束内满足要求，请调用 report_failure 说明原因。")
        return ToolOutcome(False, {"ok": False, "error_type": "DUPLICATE_SUBMISSION", "retryable": False,
                                   "message": message, "previous_result": {k: prev[k] for k in keys if k in prev}},
                           f"重复提交 {ver}（内容未修改），未重新计算",
                           arg_summary={"script": {**self._script_summary(script), "version": ver}})

    def _tool_estimate_duration(self, args):
        script = normalize_script(args.get("script"))
        fp, ver = self._version(script)
        duplicate = self._duplicate("estimate_duration", script, fp, ver, self.duration_results)
        if duplicate:
            return duplicate
        if not self.brief.target_duration_sec:
            return ToolOutcome(False, {"ok": False, "error_type": "MISSING_TARGET",
                                       "message": "任务简报缺少 target_duration_sec，无法判断时长是否达标；请向用户确认"},
                               "失败：缺少目标时长", arg_summary=self._arg_summary("estimate_duration", args))
        result = duration_tool.estimate(script, self.brief.target_duration_sec, self.brief.style,
                                        self.rules["duration_policy"])
        result["script_version"] = ver
        self.duration_results[fp] = result
        lo, hi = result["allowed_range_sec"]
        verdict = "通过" if result["passed"] else ("超时" if result["status"] == "over" else "过短")
        summary = (f"{ver}：{len(script['shots'])} 镜，预计 {result['total_sec']}s，"
                   f"目标区间 [{lo}, {hi}]s → {verdict}")
        return ToolOutcome(True, {"ok": True, **result}, summary,
                           arg_summary={"script": {**self._script_summary(script), "version": ver}})

    def _tool_check_rules(self, args):
        script = normalize_script(args.get("script"))
        fp, ver = self._version(script)
        duplicate = self._duplicate("check_rules", script, fp, ver, self.rule_results)
        if duplicate:
            return duplicate
        result = self.checker.check(script, self.brief, self.retrieved, set(self.store.by_id),
                                    self.brief_product_id())
        result["script_version"] = ver
        self.rule_results[fp] = result
        if result["passed"]:
            summary = f"{ver}：规则检查通过（提示 {len(result['warnings'])} 条）"
        else:
            codes = sorted({v["code"] for v in result["violations"]})
            summary = f"{ver}：{result['violation_count']} 项违规 {codes}"
        return ToolOutcome(True, {"ok": True, **result}, summary,
                           arg_summary={"script": {**self._script_summary(script), "version": ver}})

    def _tool_request_user_input(self, args):
        questions = [str(q) for q in (args.get("questions") or []) if str(q).strip()]
        if not questions:
            raise ValueError("questions 不能为空")
        reply = self.answers.get(questions)
        if reply:
            self.user_replies.append(reply)
            return ToolOutcome(True, {"ok": True, "user_reply": reply,
                                      "note": "用户已回复；如需更新简报字段，请调用 update_brief"},
                               f"用户回复：{reply}", arg_summary=dict(args))
        self.final = {"status": "needs_input", "questions": questions,
                      "missing": args.get("missing") or [], "reason": "等待用户补充信息"}
        return ToolOutcome(True, {"ok": True, "message": "已向用户发出补充请求，本次运行结束"},
                           f"任务暂停，等待用户回答 {len(questions)} 个问题", terminal=True,
                           final_status="needs_input", arg_summary=dict(args))

    def _tool_update_brief(self, args):
        if not self.user_replies:
            return ToolOutcome(False, {"ok": False, "error_type": "NOT_ALLOWED",
                                       "message": "只能根据用户的补充回答更新简报；请先 request_user_input"},
                               "拒绝：没有用户补充信息", arg_summary=dict(args))
        updated, rejected = {}, {}
        for key in ("platform", "target_duration_sec", "topic", "product", "audience", "style"):
            if key not in args or args[key] in (None, ""):
                continue
            if getattr(self.brief, key):
                rejected[key] = "用户已给定该字段，不允许修改"
                continue
            value = float(args[key]) if key == "target_duration_sec" else str(args[key])
            if not self._grounded_in_replies(value):
                # 真实运行发现：模型把自己假设的风格写进简报，而风格会影响时长口径（语速）
                rejected[key] = "用户回答中没有提到该内容；属于你的假设，请写进 risks，不要写入简报"
                continue
            setattr(self.brief, key, value)
            updated[key] = value
        content = {"ok": bool(updated), "updated": updated, "rejected": rejected,
                   "brief": self.brief.to_dict(), "still_missing": self.brief.missing_required()}
        budget = duration_tool.narration_budget(self.brief.target_duration_sec, self.brief.style,
                                                self.rules["duration_policy"])
        if budget and "target_duration_sec" in updated:
            content["writing_hint"] = budget
        return ToolOutcome(bool(updated), content, f"更新 {updated}；拒绝 {list(rejected)}", arg_summary=dict(args))

    def _grounded_in_replies(self, value: Any) -> bool:
        """写入简报的值必须能在用户回答里找到：数字原样出现，文本至少 60% 的字出现在回答中。"""
        replies = " ".join(self.user_replies)
        if isinstance(value, float):
            return f"{value:g}" in replies
        chars = {c for c in str(value) if not c.isspace()}
        return bool(chars) and len(chars & set(replies)) / len(chars) >= 0.6

    def _tool_submit_script(self, args):
        script = normalize_script(args.get("script"))
        fp, ver = self._version(script)
        d, r = self.duration_results.get(fp), self.rule_results.get(fp)
        problems = []
        if d is None:
            problems.append(f"{ver} 尚未调用 estimate_duration")
        elif not d["passed"]:
            problems.append(f"{ver} 时长未通过（{d['total_sec']}s）")
        if r is None:
            problems.append(f"{ver} 尚未调用 check_rules")
        elif not r["passed"]:
            problems.append(f"{ver} 规则检查有 {r['violation_count']} 项违规")
        if problems:
            return ToolOutcome(False, {"ok": False, "error_type": "VERIFICATION_REQUIRED",
                                       "message": "提交被拒绝：" + "；".join(problems) +
                                                  "。提交的脚本必须与通过检查的版本完全一致。"},
                               "提交被拒绝：" + "；".join(problems),
                               arg_summary={"script": {**self._script_summary(script), "version": ver}})
        self.final = {"status": "completed", "script": script, "script_version": ver,
                      "duration_check": d, "rule_check": r,
                      "risks": [str(x) for x in (args.get("risks") or [])]}
        return ToolOutcome(True, {"ok": True, "message": f"{ver} 已提交"},
                           f"{ver} 提交成功（{d['total_sec']}s，规则通过）", terminal=True,
                           final_status="completed",
                           arg_summary={"script": {**self._script_summary(script), "version": ver},
                                        "risks": args.get("risks")})

    def _tool_report_failure(self, args):
        best = None
        if args.get("best_script"):
            try:
                best = normalize_script(args["best_script"])
            except ScriptError:
                best = None
        final = {"status": "failed", "reason": str(args.get("reason") or ""),
                 "failed_checks": args.get("failed_checks") or [],
                 "suggestions": args.get("suggestions") or []}
        if best:
            fp, ver = self._version(best)
            final.update(script=best, script_version=ver,
                         duration_check=self.duration_results.get(fp), rule_check=self.rule_results.get(fp))
        self.final = final
        return ToolOutcome(True, {"ok": True, "message": "已记录失败原因，本次运行结束"},
                           f"明确失败：{final['reason'][:60]}", terminal=True, final_status="failed",
                           arg_summary=self._arg_summary("report_failure", args))
