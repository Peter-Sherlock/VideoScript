"""以素材定义的指标、数值、单位和条件核对量化表述。"""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Any

CN_DIGITS = "零一二两三四五六七八九十百千"
_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000}
_ARABIC = r"(?<![a-z0-9.])[-+−]?[0-9]+(?:\.[0-9]+)?"
_CHINESE = rf"负?[{CN_DIGITS}]+(?:点[零一二三四五六七八九]+)?"
_VALUE = rf"(?:{_ARABIC}|{_CHINESE})"
_UNIT = {
    "小时": r"(?:个小时|小时|hrs?\b|h\b)",
    "米": r"(?:公尺|米|m\b)",
    "分": r"分(?!贝|钟|钱|制)",
    "元": r"(?:人民币元|元|块钱|块(?!钱))",
}
_SCAN_UNIT = (r"(?:个小时|小时|分钟|秒|天|日|公里|千米|米|公尺|块钱|元|块|"
              r"百分点|分贝|分|成|倍|%|hrs?\b|h\b|m\b|db\b)")
_ANY_NUMBER = re.compile(rf"{_ARABIC}(?:\s*{_SCAN_UNIT})?|{_CHINESE}\s*{_SCAN_UNIT}")
_NEGATED = re.compile(r"(?:并非|不是|没有|非|未|不)(?:在|于)?\s*$")
_ALTERED_PREFIX = re.compile(r"(?:超过|低于|至少|至多|不足|最多|最少|不到|上限|保底|最高|最低)\s*$")
_CLAUSE_BREAK = re.compile(r"[，,。！？；;|｜/\n]")
_APPROX = r"(?:[:：]\s*)?(?:大约|约为|约|为|是|有)?"
_END = r"(?!\s*(?:以上|以下|起(?:步|售)?|起码|或更|保底))"
_CHANGE = r"(?:提升(?:至|到)|升(?:至|到)|提高(?:至|到)|变为|提(?:至|到)|到|至|→|->)"


def cn_to_number(text: str) -> float | None:
    total, current = 0, 0
    for char in text:
        if char in _CN_DIGIT:
            current = _CN_DIGIT[char]
        elif char in _CN_UNIT:
            total += (current or 1) * _CN_UNIT[char]
            current = 0
        else:
            return None
    return float(total + current)


def _number(text: str) -> Decimal:
    if text[-1].isascii():
        return Decimal(text.replace("−", "-"))
    negative = text.startswith("负")
    whole, _, fraction = text.removeprefix("负").partition("点")
    digits = "".join(str(_CN_DIGIT[char]) for char in fraction)
    value = Decimal(f"{int(cn_to_number(whole))}.{digits or '0'}")
    return -value if negative else value


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def _alternatives(aliases: list[str]) -> str:
    return "|".join(re.escape(_normalize(alias)).replace(r"\ ", r"\s*")
                    for alias in sorted(aliases, key=len, reverse=True))


def _claim_patterns(fact: dict[str, Any]) -> tuple[re.Pattern[str], ...]:
    metric = f"(?:{_alternatives(fact['aliases'])})"
    unit = _UNIT[fact["unit"]]
    if len(fact["values"]) == 2:
        return (re.compile(
            rf"{metric}\s*(?:由|从)?\s*({_VALUE})\s*(?:{unit})?\s*{_CHANGE}\s*({_VALUE})\s*{unit}{_END}"
        ),)
    return (
        re.compile(rf"{metric}\s*{_APPROX}\s*({_VALUE})\s*{unit}{_END}"),
        re.compile(rf"({_VALUE})\s*{unit}\s*(?:的)?\s*{metric}{_END}"),
    )


def _condition_spans(parts: list[str], aliases: list[str]) -> list[tuple[int, int, int]]:
    pattern = re.compile(_alternatives(aliases))
    return [(index, *match.span()) for index, text in enumerate(parts) for match in pattern.finditer(text)
            if not _NEGATED.search(text[:match.start()])]


def check_quantified_claims(parts: list[str], cited: dict[str, dict[str, Any]],
                            product_id: str | None) -> list[tuple[str, str, str]]:
    """逐字段识别声明，在同一分镜（或标题）核对该素材的适用条件。"""
    parts = [_normalize(part) for part in parts]
    covered: list[set[tuple[int, int]]] = [set() for _ in parts]
    problems = []
    expected = []
    aliases = []
    for sid, material in cited.items():
        fact = material.get("quantified_fact")
        if not fact:
            continue
        aliases.extend(fact["aliases"])
        if product_id and material["product_id"] not in (product_id, "brand"):
            continue
        values = tuple(Decimal(str(value)) for value in fact["values"])
        summary = f"{sid} {fact['metric']} {'→'.join(map(str, values))}{fact['unit']}"
        expected.append(summary)
        excluded = fact.get("excluded_subjects", [])
        wrong_subject = re.compile(_alternatives(excluded)) if excluded else None
        patterns = _claim_patterns(fact)
        matches = []
        for index, text in enumerate(parts):
            for pattern in patterns:
                for match in pattern.finditer(text):
                    prefix = _CLAUSE_BREAK.split(text[:match.start()])[-1]
                    if wrong_subject and wrong_subject.search(prefix):
                        continue
                    if _NEGATED.search(prefix) or _ALTERED_PREFIX.search(prefix):
                        continue
                    if tuple(map(_number, match.groups())) != values:
                        continue
                    matches.append((index, *match.span()))
        if not matches:
            continue
        missing, conflicting = [], []
        for condition in fact.get("conditions", []):
            label = condition["text"]
            spans = _condition_spans(parts, [label, *condition.get("aliases", [])])
            matches.extend(spans)
            if not spans:
                missing.append(label)
            opposites = condition.get("contradictions", [])
            if opposites and _condition_spans(parts, opposites):
                conflicting.append(label)
        for index, start, end in matches:
            covered[index].add((start, end))
        if missing or conflicting:
            problems.append(("UNSUPPORTED_FACT_CONDITIONS",
                             f"{summary} 的适用条件不符：缺少 {missing}，与素材冲突 {conflicting}",
                             f"在同一位置保留素材条件：{material['required_disclaimer']}。也可删除这处量化表述。"))

    # 同一已知指标后即使省略单位，中文数字也不能绕过核对。
    metric_number = re.compile(rf"(?:{_alternatives(aliases)})\s*{_APPROX}\s*({_CHINESE})")
    unsupported = []
    for text, spans in zip(parts, covered):
        quantities = [match.span() for match in _ANY_NUMBER.finditer(text)]
        for match in metric_number.finditer(text):
            if not any(start == match.start(1) for start, _ in quantities):
                quantities.append(match.span(1))
        for first, last in quantities:
            if not any(start <= first and last <= end for start, end in spans):
                unsupported.append(text[first:last])
    if unsupported:
        allowed = "、".join(expected) or "本产品没有已引用的量化素材"
        problems.append(("UNSUPPORTED_QUANTIFIED_CLAIM",
                         f"数量 {list(dict.fromkeys(unsupported))} 未匹配同一条素材的指标、数值和单位",
                         f"核对所引素材支持的声明：{allowed}。保留原指标和单位，或删除这处数量。"))
    return problems
