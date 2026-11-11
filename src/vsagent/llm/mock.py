"""离线 Mock 策略（不需要 API Key）。

边界说明：这是一个【规则驱动】的假模型，用固定启发式模拟“读工具结果 → 选下一步”，
目的是在没有模型时验证 Agent 循环、工具链、闸门、上限与 trace 是否正确。
它的决策是写死的，不能证明真实模型的决策效果；真实效果见 examples/deepseek/ 下的运行记录。
"""
from __future__ import annotations

import copy
import json
import re
from typing import Any

from .base import AssistantTurn, ToolCall

_PLATFORMS = ["抖音", "小红书", "视频号", "B站", "快手"]
_QUESTIONS = {
    "topic_or_product": "这条视频要介绍哪个产品或主题？",
    "platform": "准备发布在哪个平台（抖音/小红书/视频号/B站/快手）？",
    "target_duration_sec": "目标时长是多少秒？",
}
_TYPE_PRIORITY = {"feature": 0, "effect_data": 1, "spec": 2, "price": 3, "brand": 4}
_ELABORATION = "这一点在日常拍摄里特别实用，不用再额外折腾。"


def _norm(text: str) -> str:
    return re.sub(r"[\s·\-_/]+", "", (text or "").lower())


def _first_clause(text: str, limit: int = 16) -> str:
    return re.split(r"[，：。？！,]", text)[0][:limit]


def _strip_parens(text: str) -> str:
    return re.sub(r"（[^）]*）|\([^)]*\)", "", text).strip()


class MockPolicy:
    name = "mock/rule-policy"

    def __init__(self):
        self.brief: dict[str, Any] = {}
        self.last_tool: str | None = None
        self.counter = 0
        self.search_attempts = 0
        self.retries: dict[str, int] = {}
        self.asked = 0
        self.materials: list[dict[str, Any]] = []
        self.draft: dict[str, Any] | None = None
        self.compress_level = 0
        self.hook_shortened = False
        self.expand_count = 0
        self.fix_rounds = 0
        self.risks: list[str] = []
        self.last_args: dict[str, Any] = {}

    # ------------------------------------------------------------------
    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn:
        if not self.brief:
            m = re.search(r"<brief>(.*?)</brief>", messages[1]["content"], re.S)
            self.brief = json.loads(m.group(1)) if m else {}
        obs = None
        if messages[-1].get("role") == "tool":
            obs = json.loads(messages[-1]["content"])
        name, args = self._decide(obs)
        self.last_tool, self.last_args = name, args
        self.counter += 1
        call = ToolCall(id=f"mock_{self.counter}", name=name, arguments=json.dumps(args, ensure_ascii=False))
        message = {"role": "assistant", "content": "",
                   "tool_calls": [{"id": call.id, "type": "function",
                                   "function": {"name": name, "arguments": call.arguments}}]}
        return AssistantTurn(content="", tool_calls=[call], message=message)

    # ------------------------------------------------------------------
    def _missing(self) -> list[str]:
        b = self.brief
        missing = []
        if not (b.get("topic") or b.get("product")):
            missing.append("topic_or_product")
        if not b.get("platform"):
            missing.append("platform")
        if not b.get("target_duration_sec"):
            missing.append("target_duration_sec")
        return missing

    def _retry_or_fail(self, tool: str, obs: dict[str, Any], what: str):
        if obs.get("retryable") and self.retries.get(tool, 0) < 1:
            self.retries[tool] = self.retries.get(tool, 0) + 1
            args = dict(self.last_args)
            args["decision_reason"] = f"{tool} 返回 {obs.get('error_type')}（可重试），重试一次"
            return tool, args
        args = {"reason": f"{what}连续失败（{obs.get('error_type')}），无法完成必要的检查，不能交付未验证的脚本",
                "failed_checks": [tool],
                "suggestions": ["稍后重试", "或由人工核对时长/规则后再发布"],
                "decision_reason": f"{tool} 重试后仍失败，判断服务不可用，停止并说明"}
        if self.draft:
            args["best_script"] = self.draft
        return "report_failure", args

    def _decide(self, obs: dict[str, Any] | None):
        last = self.last_tool
        if last is None:
            missing = self._missing()
            if missing:
                return self._ask(missing)
            return self._search_initial()

        if last == "request_user_input":
            fields = self._parse_reply(obs.get("user_reply", ""))
            return "update_brief", {**fields, "decision_reason": "用户已回复，把补充的字段写入简报"}

        if last == "update_brief":
            self.brief.update(obs.get("brief") or {})
            missing = obs.get("still_missing") or self._missing()
            if missing:
                return self._ask(missing)
            return self._search_initial()

        if last == "search_materials":
            if not obs.get("ok"):
                return self._retry_or_fail("search_materials", obs, "素材检索")
            if obs["count"] == 0:
                return self._after_empty_search(obs)
            self.materials = obs["items"]
            self.draft = self._from_user_draft() or self._compose(verbose=True)
            return "estimate_duration", {"script": self.draft,
                                         "decision_reason": f"检索到 {obs['count']} 条素材，写出初稿后先估算时长"}

        if last == "estimate_duration":
            if not obs.get("ok"):
                return self._retry_or_fail("estimate_duration", obs, "时长估算")
            if obs["passed"]:
                return "check_rules", {"script": self.draft,
                                       "decision_reason": f"{obs['script_version']} 时长 {obs['total_sec']}s 达标，进行规则检查"}
            if obs["status"] == "over":
                new = self._compress()
                if new is None:
                    return self._fail_duration(obs)
                self.draft = new
                return "estimate_duration", {"script": self.draft,
                                             "decision_reason": f"超出 {obs['delta_sec']}s，压缩后重新估算"}
            new = self._expand(obs)
            if new is None:
                return self._fail_duration(obs)
            self.draft = new
            return "estimate_duration", {"script": self.draft,
                                         "decision_reason": f"短了 {obs['delta_sec']}s，延长展示镜头后重新估算"}

        if last == "check_rules":
            if not obs.get("ok"):
                return self._retry_or_fail("check_rules", obs, "规则检查")
            if obs["passed"]:
                risks = list(self.risks)
                if not self.brief.get("audience"):
                    risks.append("简报未给出受众，按“短视频创作者”泛人群撰写")
                if not any(m["type"] == "effect_data" for m in self.materials):
                    risks.append("素材中没有效果数据，脚本只陈述功能，不含效果量化结论")
                return "submit_script", {"script": self.draft, "risks": risks,
                                         "decision_reason": f"{obs['script_version']} 时长与规则均通过，提交"}
            return self._fix(obs)

        if last == "submit_script":  # 闸门拒绝时重新走一遍检查
            return "estimate_duration", {"script": self.draft, "decision_reason": "提交被拒，重新验证当前版本"}
        return "report_failure", {"reason": "Mock 策略进入未知状态", "suggestions": [],
                                  "decision_reason": "无法继续"}

    # ---- 简报 / 检索 ----
    def _ask(self, missing: list[str]):
        self.asked += 1
        if self.asked > 2:
            return "report_failure", {"reason": f"多次询问后仍缺少关键信息 {missing}", "suggestions": ["补全简报后重试"],
                                      "decision_reason": "关键信息仍缺失，停止"}
        return "request_user_input", {
            "questions": [_QUESTIONS[m] for m in missing], "missing": missing,
            "decision_reason": f"缺少关键字段 {missing}，不能猜测，向用户确认"}

    def _parse_reply(self, reply: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for p in _PLATFORMS:
            if p.lower() in reply.lower():
                fields["platform"] = p
                break
        m = re.search(r"(\d+(?:\.\d+)?)\s*(秒|s|S)", reply)
        if m:
            fields["target_duration_sec"] = float(m.group(1))
        return fields

    def _search_initial(self):
        self.search_attempts += 1
        product = self.brief.get("product")
        query = " ".join(x for x in (product, self.brief.get("topic")) if x)
        args = {"query": query, "decision_reason": "先按简报中的产品与主题检索素材"}
        if product:
            args["product"] = product
        return "search_materials", args

    def _after_empty_search(self, obs: dict[str, Any]):
        known = obs.get("known_products") or []
        wanted = _norm(self.brief.get("product") or self.brief.get("topic") or "")
        if self.search_attempts < 2:
            self.search_attempts += 1
            best, best_ratio = None, 0.0
            for name in known:
                overlap = len(set(wanted) & set(_norm(name)))
                ratio = overlap / max(len(set(wanted)), 1)
                if ratio > best_ratio:
                    best, best_ratio = name, ratio
            if best and best_ratio >= 0.4:
                return "search_materials", {
                    "query": f"{best} 卖点", "product": best,
                    "decision_reason": f"0 条结果，hint 中的“{best}”与简报产品名高度相似，疑似写法不同，改写后重查"}
            keywords = re.sub(r"帧跃|帧越|产品|介绍|视频|脚本", " ", self.brief.get("product") or self.brief.get("topic") or "")
            return "search_materials", {"query": keywords.strip() or wanted,
                                        "decision_reason": "0 条结果且现有产品都不相近，去掉品牌词用核心词再查一次"}
        return "request_user_input", {
            "questions": [f"素材库中没有“{self.brief.get('product') or self.brief.get('topic')}”的产品事实，"
                          f"请提供该产品的功能/参数资料（或确认改为现有产品：{known}）"],
            "missing": ["product_materials"],
            "decision_reason": "两次检索都没有可用素材，不能凭空编写产品事实，请用户补充"}

    # ---- 写稿 / 修改 ----
    def _product_short(self) -> str:
        for m in self.materials:
            if m["type"] != "brand":
                return m["product"]
        return self.brief.get("product") or ""

    def _from_user_draft(self) -> dict[str, Any] | None:
        """简报带了用户草稿时，直接把它作为 v1（标注内部字段以便后续压缩）。"""
        draft = self.brief.get("draft_script")
        if not isinstance(draft, dict) or not draft.get("shots"):
            return None
        draft = copy.deepcopy(draft)
        for s in draft["shots"]:
            if s.get("source_ids"):
                s["_mid"] = s["source_ids"][0]
        draft["shots"][0]["_hook"] = True
        return self._clean(draft)

    def _select_facts(self) -> list[dict[str, Any]]:
        """按优先级挑选卖点：必含要点一定保留，其余按目标时长的字数预算挑（初稿故意留 10% 余量，会偏长）。"""
        facts = sorted((m for m in self.materials if m["type"] != "brand"),
                       key=lambda m: (_TYPE_PRIORITY.get(m["type"], 9), m["id"]))
        required = self._required_ids()
        budget = float(self.brief.get("target_duration_sec") or 30) * 4.5 * 1.1 - 40  # 扣掉开头和结尾
        chosen, used = [], 0.0
        for m in facts:
            cost = len(_strip_parens(m["fact"])) + len(_ELABORATION)
            if m["id"] in required or not chosen or used + cost <= budget:
                chosen.append(m)
                used += cost
        return chosen

    def _compose(self, verbose: bool) -> dict[str, Any]:
        extra = self.brief.get("extra_requirements") or ""
        quoted = re.findall(r"[“\"‘']([^”\"’']+)[”\"’']", extra)
        hook = f"{quoted[0]}！" if quoted else "拍视频的你，是不是也常被这些细节卡住？"
        shots = [{"shot_id": 1, "visual": "近景：创作者对着镜头皱眉，画面略显杂乱", "narration": hook,
                  "subtitle": _first_clause(hook), "source_ids": [], "_hook": True}]
        for m in self._select_facts():
            line = _strip_parens(m["fact"])
            narration = f"{line}{_ELABORATION}" if verbose else line
            shots.append({"shot_id": len(shots) + 1, "visual": f"产品特写 + 讲解（对应 {m['id']}）",
                          "narration": narration, "subtitle": "" if m.get("quantified_fact") else _first_clause(line),
                          "screen_note": m.get("required_disclaimer", "") if m.get("quantified_fact") else "",
                          "source_ids": [m["id"]],
                          "_mid": m["id"]})
            if m["type"] == "feature" and not any(s.get("_demo") for s in shots):
                shots.append({"shot_id": len(shots) + 1, "visual": f"屏幕录制/实拍演示该功能（对应 {m['id']}）",
                              "narration": "", "subtitle": "实际操作演示", "hold_sec": 4.0,
                              "source_ids": [m["id"]], "_demo": True})
        if verbose:
            shots.append({"shot_id": len(shots) + 1, "visual": "生活场景混剪：户外 vlog、室内口播",
                          "narration": "不管是出门拍 vlog，还是在家录口播教程，都能派上用场。",
                          "subtitle": "vlog、口播都能用", "source_ids": [], "_scene": True})
        cta = f"{self._product_short()}，去试试吧，评论区聊聊你的拍摄需求。"
        shots.append({"shot_id": len(shots) + 1, "visual": "产品 logo 定格 + 关注引导", "narration": cta,
                      "subtitle": "评论区聊聊你的需求", "source_ids": []})
        title = _first_clause(self.brief.get("topic") or self._product_short(), 20)
        return {"title": title, "shots": shots}

    @staticmethod
    def _clean(script: dict[str, Any]) -> dict[str, Any]:
        """去掉 Mock 内部标记字段并重新编号。"""
        out = copy.deepcopy(script)
        for i, s in enumerate(out["shots"], start=1):
            s["shot_id"] = i
        return out

    def _required_ids(self) -> set[str]:
        """每个必含要点只保留优先级最高的一条承载素材。"""
        ordered = sorted(self.materials, key=lambda m: (_TYPE_PRIORITY.get(m["type"], 9), m["id"]))
        required = set()
        for point in self.brief.get("must_include") or []:
            hit = next((m for m in ordered if point in m["fact"]), None)
            if hit:
                required.add(hit["id"])
        return required

    def _compress(self) -> dict[str, Any] | None:
        """按固定顺序尝试压缩手段，每次只用一种，改动后交给工具重新估算。"""
        draft = copy.deepcopy(self.draft)
        self.compress_level += 1
        shots = draft["shots"]
        # 1) 去掉解释性句子和纯场景镜头
        if any(_ELABORATION in s["narration"] for s in shots) or any(s.get("_scene") for s in shots):
            for s in shots:
                s["narration"] = s["narration"].replace(_ELABORATION, "")
            draft["shots"] = [s for s in shots if not s.get("_scene")]
            return self._clean(draft)
        # 2) 事实句只保留第一个分句
        changed = False
        quantified_ids = {m["id"] for m in self.materials if m.get("quantified_fact")}
        for s in shots:
            if s.get("_mid") and s["_mid"] not in quantified_ids and re.search(r"[，：]", s["narration"]):
                s["narration"] = re.split(r"[，：]", s["narration"])[0] + "。"
                changed = True
        if changed:
            return self._clean(draft)
        # 3) 删掉一个优先级最低、且不是用户必含要点的事实镜头
        required = self._required_ids()
        candidates = [s for s in shots if s.get("_mid") and s["_mid"] not in required]
        if len([s for s in shots if s.get("_mid")]) > 1 and candidates:
            victim = candidates[-1]
            draft["shots"] = [s for s in shots if s is not victim]
            self.risks.append(f"为满足时长删去了 {victim['_mid']} 对应的分镜")
            return self._clean(draft)
        # 4) 缩短开头钩子、缩短演示镜头（各一次）
        if not self.hook_shortened:
            self.hook_shortened = True
            shots[0]["narration"] = "拍视频，这个细节别忽略。"
            shots[0]["subtitle"] = "这个细节别忽略"
            for s in shots:
                if s.get("_demo"):
                    s["hold_sec"] = 2.0
            return self._clean(draft)
        return None

    def _expand(self, obs: dict[str, Any]) -> dict[str, Any] | None:
        if self.expand_count >= 2:
            return None
        self.expand_count += 1
        draft = copy.deepcopy(self.draft)
        need = obs["delta_sec"] + 0.5
        fact_shots = [s for s in draft["shots"] if s.get("source_ids")] or draft["shots"]
        per = round(need / len(fact_shots), 1) + 0.1
        secs = {p["shot_id"]: p["sec"] for p in obs["per_shot"]}
        for s in fact_shots:
            s["hold_sec"] = round(secs.get(s["shot_id"], 0) + per, 1)
        return self._clean(draft)

    def _fail_duration(self, obs: dict[str, Any]):
        lo, hi = obs["allowed_range_sec"]
        return "report_failure", {
            "reason": (f"在保留用户必含要点 {self.brief.get('must_include') or []} 的前提下，"
                       f"最短也需要 {obs['total_sec']}s，超出允许区间 [{lo}, {hi}]s，无法同时满足"),
            "failed_checks": ["estimate_duration"],
            "suggestions": [f"把目标时长放宽到约 {int(obs['total_sec']) + 2} 秒", "或减少必含要点"],
            "best_script": self.draft,
            "decision_reason": "已压缩到不能再删的程度仍超时，明确报告无法满足"}

    def _fix(self, obs: dict[str, Any]):
        self.fix_rounds += 1
        codes = {v["code"] for v in obs["violations"]}
        if self.fix_rounds > 3:
            return "report_failure", {"reason": f"多轮修改后仍有违规 {sorted(codes)}", "suggestions": ["人工修改"],
                                      "failed_checks": ["check_rules"], "best_script": self.draft,
                                      "decision_reason": "规则修改轮数用尽"}
        if "MISSING_REQUIRED_POINT" in codes:
            return "report_failure", {
                "reason": "用户必含要点与时长限制冲突：保留全部要点会超时，删减又会缺要点",
                "failed_checks": ["check_rules", "estimate_duration"],
                "suggestions": ["放宽目标时长", "或减少必含要点"], "best_script": self.draft,
                "decision_reason": "缺少必含要点且无法在时长内补回，明确报告冲突"}
        draft = copy.deepcopy(self.draft)
        by_id = {m["id"]: m for m in self.materials}
        for v in obs["violations"]:
            code = v["code"]
            if code == "BANNED_WORD":
                word = re.search(r"“(.+?)”", v["detail"]).group(1)
                for s in draft["shots"]:
                    for k in ("narration", "subtitle"):
                        s[k] = s[k].replace(word, "")
                draft["title"] = draft["title"].replace(word, "")
                self.risks.append(f"用户要求中的“{word}”属于广告极限词，已删除")
            elif code == "MISSING_DISCLAIMER":
                sid = re.search(r"引用了 (\w+)", v["detail"]).group(1)
                for s in draft["shots"]:
                    if sid in s["source_ids"]:
                        note = by_id[sid]["required_disclaimer"]
                        s["screen_note"] = (s.get("screen_note", "") + " " + note).strip()
                        break
            elif code == "MISSING_BRAND_MENTION":
                draft["shots"][-1]["narration"] = "帧跃，" + draft["shots"][-1]["narration"]
            elif code == "TITLE_TOO_LONG":
                limit = int(re.search(r"上限 (\d+)", v["detail"]).group(1))
                draft["title"] = draft["title"][:limit]
            elif code in ("UNSUPPORTED_FEATURE", "UNSUPPORTED_NUMBER", "UNSUPPORTED_EFFECT_CLAIM", "MISSING_SOURCE",
                          "UNSUPPORTED_QUANTIFIED_CLAIM", "UNSUPPORTED_FACT_CONDITIONS"):
                note = f"删除了无素材依据的表述（{code}，{v['where']}）：{v['detail']}"
                if note not in self.risks:
                    self.risks.append(note)
                idx = int(v["where"].split()[-1]) - 1 if v["where"].startswith("shot") else None
                if idx is not None and draft["shots"][idx]["source_ids"]:
                    mid = draft["shots"][idx]["source_ids"][0]
                    material = by_id[mid]
                    line = _strip_parens(material["fact"])
                    current = draft["shots"][idx]
                    if material.get("quantified_fact"):
                        field = "narration" if current["narration"] else "subtitle"
                        current[field] = line
                        if field == "narration":
                            current["subtitle"] = ""
                        current["screen_note"] = material["required_disclaimer"]
                    else:
                        current["narration"] = line if current["narration"] else ""
                        current["subtitle"] = _first_clause(line)
                elif idx is not None:  # 无来源的镜头里出现了事实表述：改成不含事实的中性句
                    draft["shots"][idx]["narration"] = "来看看它能帮你做什么。"
                    draft["shots"][idx]["subtitle"] = "来看看它能做什么"
                elif v["where"] == "title":
                    draft["title"] = self._product_short()[:20]
            elif code == "WRONG_BRAND_NAME":
                for s in draft["shots"]:
                    for k in ("narration", "subtitle"):
                        s[k] = re.sub("帧越|侦跃|祯跃|帧悦", "帧跃", s[k])
        self.draft = self._clean(draft)
        return "estimate_duration", {"script": self.draft,
                                     "decision_reason": f"按违规项 {sorted(codes)} 修改，修改后重新估算时长再检查"}
