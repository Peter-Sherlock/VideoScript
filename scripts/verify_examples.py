"""独立核对 examples/ 下全部运行结果，生成 examples/verification_report.md。

用法：python scripts/verify_examples.py
对每个 output.json：用工具代码重算逐镜时长、重跑规则检查，核对素材 ID 是否真实存在且被检索过，
并把“素材 ID - 分镜 - 时长 - 检查结果”逐一列出。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vsagent.config import MATERIALS_PATH, RULES_PATH  # noqa: E402
from vsagent.tools import MaterialStore  # noqa: E402
from vsagent.verify import verify_output  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    store = MaterialStore(MATERIALS_PATH)
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    rows, details, failures = [], [], 0
    for path in sorted((ROOT / "examples").glob("*/*/output.json")):
        out = json.loads(path.read_text(encoding="utf-8"))
        rel = path.parent.relative_to(ROOT / "examples").as_posix()
        problems = verify_output(out, store, rules)
        failures += bool(problems)
        hist = " → ".join(f"{v['version']}:{v['estimated_sec']}s/{v['duration']}" if v["estimated_sec"] is not None
                          else f"{v['version']}:未估算" for v in out["revision_history"])
        rows.append(f"| {rel} | {out['status']} | {out['run']['steps_used']}/{out['run']['tool_calls_used']} "
                    f"| {out.get('estimated_total_sec') or '-'} / "
                    f"{out.get('target_duration_sec') or '-'} | {hist or '-'} | "
                    f"{', '.join(m['id'] for m in out['sources']) or '-'} | "
                    f"{'✅ 一致' if not problems else '❌ ' + '; '.join(problems)} |")
        if out["status"] == "completed":
            details.append(f"\n### {rel}（{out['script_version']}）\n\n| 镜号 | 时长(s) | 素材 ID | 旁白 |\n|---|---|---|---|")
            for s in out["shots"]:
                details.append(f"| {s['shot_id']} | {s['duration_sec']} | {', '.join(s['source_ids']) or '-'} "
                               f"| {s['narration'] or '（无旁白）'} |")
            d, r = out["checks"]["duration"], out["checks"]["rules"]
            details.append(f"\n合计 {out['estimated_total_sec']}s，区间 {d['allowed_range_sec']}；"
                           f"时长检查版本 {d['script_version']}、规则检查版本 {r['script_version']}，"
                           f"规则提示 {[w['code'] for w in r['warnings']] or '无'}")

    report = ["# 运行结果独立核对报告", "",
              "由 `python scripts/verify_examples.py` 生成：不信任 output.json 中的结论，用工具代码重新计算后比对。", "",
              "| 用例 | 状态 | 轮数/工具调用 | 预计/目标(s) | 修订轨迹 | 引用素材 | 核对 |", "|---|---|---|---|---|---|---|",
              *rows, "", "## 已完成脚本：素材 ID × 分镜 × 时长 逐一对应", *details, ""]
    (ROOT / "examples" / "verification_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"核对 {len(rows)} 个结果，{failures} 个有问题 → examples/verification_report.md")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
