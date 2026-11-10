"""时长估算工具：按口播语速把旁白折算成秒数，逐镜给出时长并与目标时长比较。

估算口径（写在这里，评审可直接核对）：
- 汉字 1 个计 1 个音节；英文单词计 1.5；阿拉伯数字按位数 × 1.3（"399" 读作“三百九十九”）。
- 语速：默认 4.5 字/秒，按风格关键词切换（见 data/brand_rules.json → duration_policy）。
- 逗号类停顿 +0.15s，句号类停顿 +0.3s，每个分镜转场 +0.3s，单镜最短 1.5s。
- 字幕按 6 字/秒计算阅读时间，每镜取“口播时间”与“字幕阅读时间”的较大值；也可用 hold_sec 指定停留时长（取较大值）。
- 角标/免责小字（screen_note）不计入时长。
- 通过条件：lower_ratio × 目标 ≤ 总时长 ≤ upper_ratio × 目标（默认 0.8 ~ 1.0）。
"""
from __future__ import annotations

import math
import re
from typing import Any

_CJK = re.compile(r"[一-鿿]")
_WORD = re.compile(r"[A-Za-z]+")
_NUM = re.compile(r"\d+(?:\.\d+)?")
_MINOR = re.compile(r"[，、；：,;:]")
_MAJOR = re.compile(r"[。！？!?…]")


def speech_units(text: str) -> float:
    text = text or ""
    units = float(len(_CJK.findall(text)))
    units += 1.5 * len(_WORD.findall(text))
    for num in _NUM.findall(text):
        digits = len(num.replace(".", ""))
        units += max(1.0, round(digits * 1.3)) + (1 if "." in num else 0)
    return units


def speech_rate_for_style(style: str | None, policy: dict[str, Any]) -> float:
    style = style or ""
    for rule in policy.get("style_chars_per_sec", []):
        if any(k in style for k in rule["keywords"]):
            return float(rule["cps"])
    return float(policy["default_chars_per_sec"])


def _cut_plan(shots: list[dict[str, Any]], need: int) -> list[dict[str, Any]]:
    """把需要删减的字数按旁白长度分摊到最长的几个镜头。
    真实运行发现：只告诉模型“约需删减 17 字”，它常常只删 2 字；给出逐镜数字更容易一次改到位。"""
    lengths = [(s["shot_id"], len(s.get("narration", ""))) for s in shots if len(s.get("narration", "")) >= 8]
    lengths.sort(key=lambda x: -x[1])
    top = lengths[:3]
    pool = sum(n for _, n in top)
    if not pool:
        return []
    plan = []
    for shot_id, n in top:
        cut = min(n - 4, math.ceil(need * n / pool))  # 每镜至少保留几个字
        if cut > 0:
            plan.append({"shot_id": shot_id, "narration_chars": n, "cut_chars": cut})
    return plan


def narration_budget(target_sec: float | None, style: str | None, policy: dict[str, Any]) -> str | None:
    """写稿参考：按估算口径，目标时长大约能容纳多少字旁白（只是参考，以 estimate 结果为准）。"""
    if not target_sec:
        return None
    cps = speech_rate_for_style(style, policy)
    aim = target_sec * (policy["lower_ratio"] + policy["upper_ratio"]) / 2
    overhead = min(2.5, aim * 0.25)  # 转场与停顿的大致开销
    chars = int((aim - overhead) * cps)
    return (f"写稿参考：按当前风格语速约 {cps:g} 字/秒，建议总时长约 {aim:.1f}s，"
            f"旁白总字数大约 {chars} 字以内（含标点停顿与转场的粗略估计，最终以 estimate_duration 为准）。")


def estimate(script: dict[str, Any], target_sec: float, style: str | None,
             policy: dict[str, Any]) -> dict[str, Any]:
    cps = speech_rate_for_style(style, policy)
    read_cps = policy["subtitle_read_cps"]
    per_shot = []
    for shot in script["shots"]:
        narration, subtitle = shot.get("narration", ""), shot.get("subtitle", "")
        body, basis = 0.0, "无旁白/字幕"
        if narration:
            units = speech_units(narration)
            pauses = (len(_MINOR.findall(narration)) * policy["minor_pause_sec"]
                      + len(_MAJOR.findall(narration)) * policy["major_pause_sec"])
            body = units / cps + pauses
            basis = f"旁白 {units:g} 音节 ÷ {cps:g} 字/秒 + 停顿 {pauses:.2f}s"
        if subtitle:
            # 字幕也要留够阅读时间：真实运行中模型曾把卖点挪进长字幕、只保留极短口播来压时长
            read = speech_units(subtitle) / read_cps
            if read > body:
                body = read
                basis = (basis + "；" if narration else "") + f"字幕 {speech_units(subtitle):g} 字按 {read_cps:g} 字/秒阅读（较长，取此值）"
        sec = max(policy["min_shot_sec"], body + policy["shot_transition_sec"])
        if shot.get("hold_sec", 0) > sec:
            sec = shot["hold_sec"]
            basis += f"；按 hold_sec={shot['hold_sec']:g}s 计"
        per_shot.append({"shot_id": shot["shot_id"], "sec": round(sec, 1), "basis": basis})

    total = round(sum(s["sec"] for s in per_shot), 1)
    lower = round(target_sec * policy["lower_ratio"], 1)
    upper = round(target_sec * policy["upper_ratio"], 1)
    # 建议值取区间中部：真实运行发现模型只按“超出上限多少”修改时，会每次删一两个字、贴着上限反复估算
    aim = round((lower + upper) / 2, 1)
    cut_plan: list[dict[str, Any]] = []
    if total > upper:
        status, delta = "over", round(total - upper, 1)
        need = math.ceil((total - aim) * cps)
        cut_plan = _cut_plan(script["shots"], need)
        plan_text = "、".join(f"镜头{p['shot_id']}删约{p['cut_chars']}字" for p in cut_plan)
        suggestion = (f"超出上限 {delta}s。建议一次压到约 {aim}s（区间中部，留出余量），"
                      f"约需删减 {need} 个字的旁白。可参考：{plan_text}（也可直接删除/合并分镜）；修改后需重新估算")
    elif total < lower:
        status, delta = "under", round(lower - total, 1)
        suggestion = (f"低于下限 {delta}s。建议补到约 {aim}s：可补充约 {math.ceil((aim - total) * cps)} 字"
                      f"【有素材依据】的内容，或给展示镜头设置 hold_sec；不得为凑时长编造事实")
    else:
        status, delta, suggestion = "ok", 0.0, "时长符合要求"
    return {
        "passed": status == "ok",
        "status": status,
        "total_sec": total,
        "target_sec": target_sec,
        "allowed_range_sec": [lower, upper],
        "recommended_sec": aim,
        "cut_plan": cut_plan,
        "delta_sec": delta,
        "speech_rate_cps": cps,
        "per_shot": per_shot,
        "suggestion": suggestion,
    }
