"""独立核对输出：把素材 ID、分镜时长、检查结果逐一对应（供测试和 scripts/verify_examples.py 使用）。

不信任 output.json 里的结论，而是用工具代码重新计算一遍再比较。
"""
from __future__ import annotations

from typing import Any

from .schema import Brief, normalize_script
from .tools import duration as duration_tool
from .tools.materials import MaterialStore
from .tools.rules import RuleChecker


def verify_output(output: dict[str, Any], store: MaterialStore, rules: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    status = output.get("status")
    run = output.get("run", {})
    limits = run.get("limits", {})
    if run.get("steps_used", 0) > limits.get("max_steps", 10**9):
        problems.append("决策轮数超过上限")
    if run.get("tool_calls_used", 0) > limits.get("max_tool_calls", 10**9):
        problems.append("工具调用次数超过上限")

    if status == "completed":
        problems += _verify_completed(output, store, rules)
    elif status == "needs_input":
        if not output.get("questions"):
            problems.append("needs_input 但没有给出问题")
    elif status == "failed":
        if not (output.get("failure") or {}).get("reason") and not output.get("status_reason"):
            problems.append("failed 但没有说明原因")
    elif status == "incomplete":
        if "上限" not in output.get("status_reason", ""):
            problems.append("incomplete 但没有说明达到的上限")
    else:
        problems.append(f"未知状态 {status}")
    return problems


def _verify_completed(output, store, rules) -> list[str]:
    problems = []
    checks = output["checks"]
    d, r = checks.get("duration"), checks.get("rules")
    if not d or not d["passed"]:
        problems.append("completed 但时长检查未通过")
    if not r or not r["passed"]:
        problems.append("completed 但规则检查未通过")
    version = output.get("script_version")
    for label, check in (("时长", d), ("规则", r)):
        if check and check.get("script_version") != version:
            problems.append(f"{label}检查版本 {check.get('script_version')} 与交付脚本版本 {version} 不一致")

    shots = output["shots"]
    total = round(sum(s["duration_sec"] for s in shots), 1)
    if abs(total - output["estimated_total_sec"]) > 0.05:
        problems.append(f"分镜时长之和 {total} ≠ 预计总时长 {output['estimated_total_sec']}")

    retrieved = set(output.get("retrieval", {}).get("retrieved_ids", []))
    listed = {m["id"] for m in output.get("sources", [])}
    for s in shots:
        for sid in s["source_ids"]:
            if sid not in store.by_id:
                problems.append(f"分镜 {s['shot_id']} 引用了不存在的素材 {sid}")
            if sid not in retrieved:
                problems.append(f"分镜 {s['shot_id']} 引用的 {sid} 不在本次检索结果中")
            if sid not in listed:
                problems.append(f"{sid} 未出现在素材来源列表")

    # 用工具代码独立重算
    script = normalize_script({"title": output["title"], "shots": [
        {k: s.get(k) for k in ("visual", "narration", "subtitle", "screen_note", "hold_sec", "source_ids")}
        for s in shots]})
    brief = Brief.from_dict(output["brief_final"])
    if missing := brief.missing_required():
        return [*problems, f"completed 但最终简报缺少关键字段：{missing}"]
    re_d = duration_tool.estimate(script, brief.target_duration_sec, brief.style, rules["duration_policy"])
    for s, p in zip(shots, re_d["per_shot"]):
        if abs(p["sec"] - s["duration_sec"]) > 0.05:
            problems.append(f"分镜 {s['shot_id']} 重算时长 {p['sec']}s ≠ 输出 {s['duration_sec']}s")
    if not re_d["passed"]:
        problems.append(f"独立重算总时长 {re_d['total_sec']}s 不在允许区间 {re_d['allowed_range_sec']}")
    checker = RuleChecker(rules, store.brand)
    product = store.resolve_product(brief.product)
    re_r = checker.check(script, brief, {i: store.by_id[i] for i in retrieved if i in store.by_id},
                         set(store.by_id), product["product_id"] if product else None)
    if not re_r["passed"]:
        problems.append(f"独立重跑规则检查未通过：{[v['code'] for v in re_r['violations']]}")
    return problems
