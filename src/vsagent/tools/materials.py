"""素材检索工具：在本地合成素材库中按产品与关键词检索事实。

检索策略刻意保持简单、可解释：
- 指定 product 时做严格过滤（与名称/别名归一化后精确匹配），匹配不上就返回空，并给出现有产品列表作为提示；
- 未指定 product 时，从 query 中识别产品名，再按关键词命中与字符二元组重叠打分。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SPACE = re.compile(r"[\s·\-_/、，,。.!！?？:：]+")


def _norm(text: str) -> str:
    return _SPACE.sub("", (text or "").lower())


def _bigrams(text: str) -> set[str]:
    t = _norm(text)
    return {t[i:i + 2] for i in range(len(t) - 1)}


class MaterialStore:
    def __init__(self, path: Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.brand: dict[str, Any] = data["brand"]
        self.products: list[dict[str, Any]] = data["products"]
        self.materials: list[dict[str, Any]] = data["materials"]
        self.by_id = {m["id"]: m for m in self.materials}

    # ---- 产品识别 ----
    def _product_names(self, product: dict[str, Any]) -> list[str]:
        return [product["name"], *product.get("aliases", [])]

    def resolve_product(self, name: str | None) -> dict[str, Any] | None:
        """严格匹配：归一化后与产品名或别名相等。"""
        if not name:
            return None
        key = _norm(name)
        for product in self.products:
            if any(_norm(n) == key for n in self._product_names(product)):
                return product
        return None

    def detect_product_in_query(self, query: str) -> dict[str, Any] | None:
        q = _norm(query)
        best, best_len = None, 0
        for product in self.products:
            for n in self._product_names(product):
                nn = _norm(n)
                if nn and nn in q and len(nn) > best_len:
                    best, best_len = product, len(nn)
        return best

    def product_name(self, product_id: str) -> str:
        if product_id == "brand":
            return f"{self.brand['name']}（品牌通用）"
        for p in self.products:
            if p["product_id"] == product_id:
                return p["name"]
        return product_id

    # ---- 检索 ----
    def _score(self, material: dict[str, Any], query: str) -> float:
        q = _norm(query).replace(_norm(self.brand["name"]), "")  # 仅品牌名命中不算相关
        if not q:
            return 0.0
        score = 0.0
        for kw in material.get("keywords", []):
            if _norm(kw) and _norm(kw) in q:
                score += 3.0
        overlap = _bigrams(q) & _bigrams(material["fact"])
        score += 0.5 * len(overlap)
        return score

    def search(self, query: str, product: str | None = None,
               material_types: list[str] | None = None, top_k: int = 8) -> dict[str, Any]:
        query = (query or "").strip()
        if not query and not product:
            raise ValueError("query 与 product 不能同时为空")
        types = {t.strip() for t in (material_types or []) if t and t.strip()}
        known = [p["name"] for p in self.products]

        target = None
        if product:
            target = self.resolve_product(product)
            if target is None:
                return {
                    "count": 0, "items": [],
                    "hint": f"product 参数“{product}”未匹配任何产品（严格匹配名称/别名）。素材库现有产品：{known}",
                    "known_products": known,
                }
        else:
            target = self.detect_product_in_query(query)

        scored = []
        for m in self.materials:
            if types and m["type"] not in types:
                continue
            if target is not None:
                # 已识别产品：返回该产品全部素材（按相关度排序）+ 与 query 相关的品牌素材
                if m["product_id"] == target["product_id"]:
                    scored.append((self._score(m, query) + 2.0, m))
                elif m["product_id"] == "brand" and self._score(m, query) >= 2.0:
                    scored.append((self._score(m, query), m))
            else:
                s = self._score(m, query)
                if s >= 2.0:
                    scored.append((s, m))

        scored.sort(key=lambda x: (-x[0], x[1]["id"]))
        items = [self.public_view(m) for _, m in scored[:top_k]]
        result: dict[str, Any] = {"count": len(items), "items": items}
        if not items:
            result["hint"] = f"没有与“{query or product}”相关的素材。素材库现有产品：{known}"
            result["known_products"] = known
        return result

    def public_view(self, m: dict[str, Any]) -> dict[str, Any]:
        view = {
            "id": m["id"],
            "product": self.product_name(m["product_id"]),
            "type": m["type"],
            "fact": m["fact"],
            "source": m["source"],
        }
        if m.get("required_disclaimer"):
            view["required_disclaimer"] = m["required_disclaimer"]
        return view
