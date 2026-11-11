"""规则检查工具：事实可追溯 + 品牌规则 + 平台规则 + 用户硬性要求。

确定性规则（不调用模型），每条违规都带 code / 位置 / 修改建议，方便模型据此修改：
- UNKNOWN_SOURCE        引用了不存在或本次会话没检索到的素材 ID
- MISSING_SOURCE        分镜出现功能/数字表述，但没有标注素材来源
- UNSUPPORTED_FEATURE   提到的功能词在所引素材中找不到
- UNSUPPORTED_NUMBER    数字（含 80%、八成、两倍等）在所引素材中找不到
- UNSUPPORTED_QUANTIFIED_CLAIM  指标、数值、单位无法共同匹配一条量化素材
- UNSUPPORTED_FACT_CONDITIONS   量化声明缺少同镜适用条件，或与素材条件冲突
- UNSUPPORTED_EFFECT_CLAIM  量化或强化的效果结论（如“效率提升80%”“大幅提升”）没有效果数据素材支撑
- BANNED_WORD / WRONG_BRAND_NAME / MISSING_BRAND_MENTION / MISSING_DISCLAIMER
- MISSING_TITLE / TITLE_TOO_LONG / MISSING_REQUIRED_POINT
提示（不阻断）：EFFECT_CLAIM_NEEDS_REVIEW（定性效率表述）、CROSS_PRODUCT_SOURCE（引用了其它产品素材）、
              FEATURE_MENTION_NO_SOURCE（无来源镜头提到功能词，但没有品牌名/宣称词，视为话题而非产品宣称）
"""
from __future__ import annotations

import re
from typing import Any

from ..schema import shot_text
from .facts import check_quantified_claims, cn_to_number

_ARABIC = re.compile(r"(?<![A-Za-z0-9.])\d+(?:\.\d+)?")
_CN_NUM = re.compile(r"([零一二两三四五六七八九十百千]+)\s*(成|倍|小时|个小时|分钟|秒|天|公里|米|公尺|元|块|分|%|个百分点)")
_QUANTITY = re.compile(r"\d|%|倍|[一二两三四五六七八九十]成|翻倍")


def extract_numbers(text: str) -> set[float]:
    nums = {float(n) for n in _ARABIC.findall(text or "")}
    for cn, _unit in _CN_NUM.findall(text or ""):
        value = cn_to_number(cn)
        if value is not None:
            nums.add(value)
    return nums


def _fmt(n: float) -> str:
    return f"{n:g}"


def _contains(text: str, term: str) -> bool:
    return term.lower() in text.lower()


class RuleChecker:
    def __init__(self, rules: dict[str, Any], brand: dict[str, Any]):
        self.rules = rules
        self.brand = brand
        self.banned_regex = [(re.compile(r["pattern"]), r["label"]) for r in rules.get("banned_regex", [])]

    def platform_key(self, platform: str | None) -> str:
        if not platform:
            return "default"
        return self.rules["platform_aliases"].get(platform.strip().lower(),
                                                  self.rules["platform_aliases"].get(platform.strip(), "default"))

    # ------------------------------------------------------------------
    def check(self, script: dict[str, Any], brief: Any, retrieved: dict[str, dict[str, Any]],
              all_ids: set[str], brief_product_id: str | None = None) -> dict[str, Any]:
        violations: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        def add(bucket, code, where, detail, suggestion):
            bucket.append({"code": code, "where": where, "detail": detail, "suggestion": suggestion})

        title = script.get("title", "")
        all_cited: dict[str, dict[str, Any]] = {}
        full_text_parts = [title]

        for shot in script["shots"]:
            where = f"shot {shot['shot_id']}"
            text = shot_text(shot)
            full_text_parts.append(text)
            cited = {}
            for sid in shot["source_ids"]:
                if sid in retrieved:
                    cited[sid] = retrieved[sid]
                elif sid in all_ids:
                    add(violations, "UNKNOWN_SOURCE", where, f"{sid} 存在于素材库但本次会话未检索到，不能引用",
                        "先用 search_materials 检索到该素材，或删除该引用")
                else:
                    add(violations, "UNKNOWN_SOURCE", where, f"素材 ID {sid} 不存在", "只能引用检索结果中的素材 ID")
            all_cited.update(cited)
            self._check_claims([shot[key] for key in ("narration", "subtitle", "screen_note")],
                               cited, where, violations, warnings, add, brief_product_id)
            if brief_product_id:
                others = [sid for sid, m in cited.items() if m["product_id"] not in (brief_product_id, "brand")]
                if others:
                    add(warnings, "CROSS_PRODUCT_SOURCE", where, f"引用了其它产品的素材 {others}",
                        "确认是否需要跨产品引用")

        # 标题：没有单独的来源字段，按全片已引用素材核对
        self._check_claims([title], all_cited, "title", violations, warnings, add, brief_product_id)

        full_text = " ".join(full_text_parts)
        self._check_banned(full_text, violations, add)
        self._check_brand(full_text, violations, add)
        self._check_disclaimers(script, all_cited, full_text, violations, add)
        self._check_title(title, brief, violations, add)
        # 必含要点必须出现在视频里的旁白或字幕中；只写在标题（发布文案）或角标小字里不算
        main_text = " ".join(f"{s['narration']} {s['subtitle']}" for s in script["shots"])
        for point in getattr(brief, "must_include", []) or []:
            if not _contains(main_text, point):
                add(violations, "MISSING_REQUIRED_POINT", "global",
                    f"用户要求必须包含“{point}”，旁白/字幕中未出现（只写在标题或角标小字里不算）",
                    "补充该要点；若与时长冲突无法同时满足，应明确说明")

        return {
            "passed": not violations,
            "violation_count": len(violations),
            "violations": violations,
            "warnings": warnings,
            "source_ids_used": sorted(all_cited),
            "rules_checked": [
                "素材来源可追溯", "功能/效果表述有据", "量化声明的指标、数值、单位及条件", "广告极限词", "品牌名称与露出",
                "免责声明", "平台标题长度", "用户必含要点",
            ],
        }

    # ------------------------------------------------------------------
    def _check_claims(self, parts, cited, where, violations, warnings, add, product_id):
        text = " ".join(part for part in parts if part)
        if not text:
            return
        cited_text = " ".join(m["fact"] + " " + " ".join(m.get("keywords", [])) for m in cited.values())
        # 1) 功能词必须能在所引素材中找到
        is_claim = self.brand["name"] in text or any(m in text for m in self.rules.get("claim_markers", []))
        for term in self.rules["feature_lexicon"]:
            if _contains(text, term):
                if not cited and is_claim:
                    add(violations, "MISSING_SOURCE", where, f"宣称了“{term}”相关能力但未标注素材来源",
                        "在 source_ids 中标注支撑该功能的素材 ID，或删除该表述")
                elif not cited:  # 只是提到痛点/话题（如“还在手动打字幕？”），不算产品宣称
                    add(warnings, "FEATURE_MENTION_NO_SOURCE", where, f"提到“{term}”但未标注来源（未识别为产品宣称）",
                        "若是在描述产品能力，请补充 source_ids")
                elif not _contains(cited_text, term):
                    add(violations, "UNSUPPORTED_FEATURE", where,
                        f"“{term}”在所引素材 {sorted(cited)} 中找不到依据", "删除该功能表述，或引用确有该功能的素材")
        # 2) 量化素材要求同一条素材支持完整声明，其余素材沿用数字来源检查。
        if any(m.get("quantified_fact") for m in cited.values()):
            for code, detail, suggestion in check_quantified_claims(parts, cited, product_id):
                add(violations, code, where, detail, suggestion)
        else:
            missing = sorted(extract_numbers(text) - extract_numbers(cited_text))
            if missing and not cited:
                add(violations, "MISSING_SOURCE", where, f"出现数字 {[_fmt(n) for n in missing]} 但未标注素材来源",
                    "数字必须来自素材；标注来源或删除数字")
            elif missing:
                add(violations, "UNSUPPORTED_NUMBER", where,
                    f"数字 {[_fmt(n) for n in missing]} 在所引素材 {sorted(cited)} 中找不到",
                    "删除或改为素材中的原始数字，不得估算/编造")
        # 3) 效果结论
        has_effect_data = any(m["type"] == "effect_data" for m in cited.values())
        verbs = [v for v in self.rules["effect_verbs"] if v in text]
        if verbs and not has_effect_data:
            if _QUANTITY.search(text):
                add(violations, "UNSUPPORTED_EFFECT_CLAIM", where,
                    f"出现量化效果表述（{'/'.join(verbs)} + 数量），但没有效果数据素材支撑",
                    "删除量化效果结论（如“效率提升80%”），改为描述素材中的功能本身")
            elif any(i in text for i in self.rules["intensifiers"]):
                add(violations, "UNSUPPORTED_EFFECT_CLAIM", where,
                    "出现“大幅/显著”等强化效果表述，但没有效果数据素材支撑", "删除强化词，只陈述功能事实")
            elif any(n in text for n in self.rules["efficiency_nouns"]):
                add(warnings, "EFFECT_CLAIM_NEEDS_REVIEW", where,
                    "出现定性的效率/成本表述，素材中无效果数据", "建议改写为功能描述，或在风险中注明")

    def _check_banned(self, text, violations, add):
        hits = [w for w in self.rules["banned_words"] if _contains(text, w)]
        hits += [label for rx, label in self.banned_regex if rx.search(text)]
        for w in sorted(set(hits)):
            add(violations, "BANNED_WORD", "global", f"出现广告极限词“{w}”", "删除或改为客观描述")
        for variant in self.brand.get("forbidden_variants", []):
            if variant in text:
                add(violations, "WRONG_BRAND_NAME", "global", f"品牌名写成了“{variant}”",
                    f"统一写作“{self.brand['name']}”")

    def _check_brand(self, text, violations, add):
        if self.rules.get("brand_mention_required") and self.brand["name"] not in text:
            add(violations, "MISSING_BRAND_MENTION", "global", f"全片未出现品牌名“{self.brand['name']}”",
                "在旁白或字幕中至少露出一次品牌名")

    def _check_disclaimers(self, script, cited, text, violations, add):
        for sid, m in sorted(cited.items()):
            if not m.get("required_disclaimer"):
                continue
            if not any(k in text for k in m.get("disclaimer_keywords", [])):
                shot_ids = [s["shot_id"] for s in script["shots"] if sid in s["source_ids"]]
                add(violations, "MISSING_DISCLAIMER", f"shot {shot_ids[0]}" if shot_ids else "global",
                    f"引用了 {sid}，缺少必需的说明“{m['required_disclaimer']}”",
                    f"在引用 {sid} 的分镜 screen_note 中加上：{m['required_disclaimer']}（screen_note 不计入口播时长）")

    def _check_title(self, title, brief, violations, add):
        if not title:
            add(violations, "MISSING_TITLE", "title", "缺少标题", "补充标题")
            return
        key = self.platform_key(getattr(brief, "platform", None))
        limit = self.rules["platform_rules"][key]["title_max_chars"]
        if len(title) > limit:
            add(violations, "TITLE_TOO_LONG", "title",
                f"标题 {len(title)} 字，超过{self.rules['platform_rules'][key]['label']}上限 {limit} 字",
                f"压缩到 {limit} 字以内")
