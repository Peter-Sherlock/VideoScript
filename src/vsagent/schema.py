"""数据结构：任务简报 Brief、脚本 Script 的解析、校验与版本指纹。"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any

BRIEF_FIELDS = (
    "topic", "product", "audience", "platform", "target_duration_sec",
    "style", "must_include", "extra_requirements", "request", "draft_script",
)


def parse_target_duration(value: Any) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("target_duration_sec 必须是有限正数（秒）") from exc
    if isinstance(value, bool) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("target_duration_sec 必须是有限正数（秒）")
    return seconds


@dataclass
class Brief:
    topic: str | None = None
    product: str | None = None
    audience: str | None = None
    platform: str | None = None
    target_duration_sec: float | None = None
    style: str | None = None
    must_include: list[str] = field(default_factory=list)
    extra_requirements: str | None = None
    request: str | None = None  # 用户原话（可选）
    draft_script: Any = None    # 用户自带的草稿（可选），Agent 在其基础上修改

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Brief":
        if not isinstance(data, dict):
            raise ValueError("brief 必须是 JSON 对象")
        kwargs = {k: data.get(k) for k in BRIEF_FIELDS if k in data}
        for key in ("topic", "product", "audience", "platform", "style", "extra_requirements", "request"):
            value = kwargs.get(key)
            if value is not None:
                if not isinstance(value, str):
                    raise ValueError(f"brief.{key} 必须是字符串")
                kwargs[key] = value.strip() or None
        points = kwargs.get("must_include")
        if points is not None and (not isinstance(points, list) or any(not isinstance(x, str) for x in points)):
            raise ValueError("brief.must_include 必须是字符串数组")
        kwargs["must_include"] = [x.strip() for x in points or [] if x.strip()]
        target = kwargs.get("target_duration_sec")
        kwargs["target_duration_sec"] = None if target in (None, "") else parse_target_duration(target)
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def missing_required(self) -> list[str]:
        """生成脚本必须具备的字段；缺失时不能靠猜测补齐。"""
        missing = []
        if not (self.topic or self.product):
            missing.append("topic_or_product")
        if not self.platform:
            missing.append("platform")
        if not self.target_duration_sec:
            missing.append("target_duration_sec")
        return missing

    def missing_optional(self) -> list[str]:
        return [name for name in ("audience", "style") if not getattr(self, name)]


class ScriptError(ValueError):
    """模型提交的脚本结构不合法。"""


def normalize_script(raw: Any) -> dict[str, Any]:
    """把模型传入的脚本整理成统一结构；结构错误时抛 ScriptError（作为工具错误返回给模型）。"""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ScriptError(f"script 不是合法 JSON：{exc}") from exc
    if not isinstance(raw, dict):
        raise ScriptError("script 必须是对象，包含 title 与 shots")
    shots_raw = raw.get("shots")
    if not isinstance(shots_raw, list) or not shots_raw:
        raise ScriptError("script.shots 必须是非空数组")

    shots = []
    for idx, shot in enumerate(shots_raw, start=1):
        if not isinstance(shot, dict):
            raise ScriptError(f"第 {idx} 个分镜不是对象")
        source_ids = shot.get("source_ids")
        if source_ids is None:
            source_ids = []
        if isinstance(source_ids, str):
            source_ids = [s.strip() for s in source_ids.replace("，", ",").split(",")]
        if not isinstance(source_ids, list) or any(not isinstance(s, str) for s in source_ids):
            raise ScriptError(f"第 {idx} 个分镜 source_ids 必须是字符串数组")
        raw_hold = shot.get("hold_sec")
        try:
            hold = float(raw_hold) if raw_hold not in (None, "") else 0.0
        except (TypeError, ValueError, OverflowError) as exc:
            raise ScriptError(f"第 {idx} 个分镜 hold_sec 不是数字") from exc
        if isinstance(raw_hold, bool) or not math.isfinite(hold) or hold < 0:
            raise ScriptError(f"第 {idx} 个分镜 hold_sec 必须是有限非负数")
        norm = {
            "shot_id": idx,  # 统一按顺序重新编号，保证分镜号与时长表一一对应
            "visual": str(shot.get("visual") or "").strip(),
            "narration": str(shot.get("narration") or "").strip(),
            "subtitle": str(shot.get("subtitle") or "").strip(),
            "screen_note": str(shot.get("screen_note") or "").strip(),
            "hold_sec": round(hold, 1),
            "source_ids": sorted({s.strip().upper() for s in source_ids if s.strip()}),
        }
        if not norm["visual"]:
            raise ScriptError(f"第 {idx} 个分镜缺少 visual（画面描述）")
        if not (norm["narration"] or norm["subtitle"] or norm["hold_sec"]):
            raise ScriptError(f"第 {idx} 个分镜没有旁白、字幕或 hold_sec，无法估算时长")
        shots.append(norm)
    return {"title": str(raw.get("title") or "").strip(), "shots": shots}


def script_fingerprint(script: dict[str, Any]) -> str:
    """同一内容的脚本得到同一指纹，用于把检查结果绑定到具体版本。"""
    payload = json.dumps(script, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]


def shot_text(shot: dict[str, Any]) -> str:
    """一个分镜里所有会被观众看到/听到的文字。"""
    return " ".join(x for x in (shot.get("narration"), shot.get("subtitle"), shot.get("screen_note")) if x)
