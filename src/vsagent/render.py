"""把最终输出渲染成便于编辑/审阅的 Markdown。"""
from __future__ import annotations

from typing import Any

STATUS_LABEL = {
    "completed": "✅ completed（已完成）",
    "needs_input": "⏸ needs_input（等待用户补充）",
    "failed": "❌ failed（明确失败）",
    "incomplete": "⚠ incomplete（达到执行上限，未完成）",
}


def _c(text: Any) -> str:
    return str(text if text not in (None, "") else "-").replace("|", "\\|").replace("\n", " ")


def render_markdown(out: dict[str, Any]) -> str:
    lines = [f"# {out.get('title') or '（未生成可交付标题）'}", ""]
    lines.append(f"- 任务状态：**{STATUS_LABEL.get(out['status'], out['status'])}** — {out['status_reason']}")
    lines.append(f"- 平台：{_c(out.get('platform'))}；目标时长：{_c(out.get('target_duration_sec'))}s；"
                 f"预计总时长：**{_c(out.get('estimated_total_sec'))}s**（脚本 {_c(out.get('script_version'))}）")
    lines.append(f"- 模型：`{out['run']['llm']}`；决策轮数 {out['run']['steps_used']}，"
                 f"工具调用 {out['run']['tool_calls_used']} 次")
    lines.append("")

    if out.get("questions"):
        lines += ["## 需要你补充的信息", ""] + [f"- {q}" for q in out["questions"]] + [""]
    if out.get("failure"):
        f = out["failure"]
        lines += ["## 无法满足的原因与建议", "", f"- 原因：{f.get('reason')}"]
        if f.get("failed_checks"):
            lines.append(f"- 未通过的检查：{f['failed_checks']}")
        lines += [f"- 建议：{s}" for s in f.get("suggestions") or []] + [""]

    if out.get("shots"):
        header = "## 分镜脚本" if out["status"] == "completed" else "## 草稿分镜（未通过全部检查，仅供参考）"
        lines += [header, "", "| 镜号 | 时长(s) | 画面 | 旁白 | 字幕 | 角标/说明 | 素材来源 |",
                  "|---|---|---|---|---|---|---|"]
        for s in out["shots"]:
            lines.append(f"| {s['shot_id']} | {_c(s['duration_sec'])} | {_c(s['visual'])} | {_c(s['narration'])} "
                         f"| {_c(s['subtitle'])} | {_c(s['screen_note'])} | {_c(', '.join(s['source_ids']))} |")
        lines.append("")

    if out.get("sources"):
        lines += ["## 素材来源", "", "| ID | 类型 | 事实 | 出处 |", "|---|---|---|---|"]
        for m in out["sources"]:
            lines.append(f"| {m['id']} | {m['type']} | {_c(m['fact'])} | {_c(m['source'])} |")
        lines.append("")

    lines += ["## 检查结果", ""]
    d, r = out["checks"].get("duration"), out["checks"].get("rules")
    if d:
        lo, hi = d["allowed_range_sec"]
        lines.append(f"- 时长（{d['script_version']}）：{d['total_sec']}s，允许区间 [{lo}, {hi}]s → "
                     f"{'通过' if d['passed'] else '未通过（' + d['status'] + '）'}；语速 {d['speech_rate_cps']} 字/秒")
    else:
        lines.append("- 时长：未完成估算")
    if r:
        lines.append(f"- 规则（{r['script_version']}）：{'通过' if r['passed'] else '未通过'}，"
                     f"违规 {len(r['violations'])} 项，提示 {len(r['warnings'])} 项")
        lines += [f"  - [{v['code']}] {v['where']}：{v['detail']}" for v in r["violations"]]
    else:
        lines.append("- 规则：未完成检查")
    lines.append("")

    if out.get("revision_history"):
        lines += ["## 修订记录", "", "| 版本 | 预计时长(s) | 时长检查 | 规则检查 |", "|---|---|---|---|"]
        for v in out["revision_history"]:
            lines.append(f"| {v['version']} | {_c(v['estimated_sec'])} | {_c(v['duration'])} | {_c(v['rules'])} |")
        lines.append("")

    risks = list(out.get("risks") or []) + list(out.get("system_notes") or [])
    lines += ["## 风险与说明", ""] + ([f"- {x}" for x in risks] or ["- 无"]) + [""]
    return "\n".join(lines)
