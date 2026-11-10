"""端到端场景：用离线 Mock 策略跑 examples/inputs 下全部用例，覆盖题目全部必须验收点。

注意：Mock 只验证流程（工具链、闸门、上限、trace、输出结构），不证明真实模型的决策效果。
"""
import json
import os

import pytest

from vsagent.cli import load_case, run_case
from vsagent.config import ROOT
from vsagent.verify import verify_output

INPUTS = ROOT / "examples" / "inputs"
EXPECTED = {
    "01_normal": "completed",
    "02_reference_p01": "completed",
    "02b_reference_user_draft": "completed",
    "03_missing_info": "needs_input",
    "03b_missing_info_answered": "completed",
    "04_no_material": "needs_input",
    "05_query_rewrite": "completed",
    "06_tool_failure_transient": "completed",
    "07_tool_failure_permanent": "failed",
    "08_overtime_infeasible": "failed",
    "09_rule_violation": "completed",
    "10_step_limit": "incomplete",
}


@pytest.fixture(scope="module")
def outputs():
    return {cid: run_case(load_case(INPUTS / f"{cid}.json"), "mock", None) for cid in EXPECTED}


@pytest.mark.parametrize("case_id", list(EXPECTED))
def test_status_and_independent_verification(outputs, store, rules, case_id):
    out = outputs[case_id]
    assert out["status"] == EXPECTED[case_id], out["status_reason"]
    assert verify_output(out, store, rules) == []


def test_reference_case_compresses_and_never_fabricates(outputs):
    out = outputs["02_reference_p01"]
    history = out["revision_history"]
    assert history[0]["duration"] == "over" and history[-1]["duration"] == "ok"
    assert history[0]["estimated_sec"] > 30 >= out["estimated_total_sec"]
    assert {m["id"] for m in out["sources"]} == {"P01"}
    text = json.dumps(out["shots"], ensure_ascii=False)
    assert "80" not in text and "效率提升" not in text


def test_reference_user_draft_38s_is_compressed_and_cleaned(outputs):
    """参考实例的压缩路径：用户草稿约 38s 且含“效率提升80%”，改到 30s 内并删掉无依据结论。"""
    out = outputs["02b_reference_user_draft"]
    first, last = out["revision_history"][0], out["revision_history"][-1]
    assert first["duration"] == "over" and first["estimated_sec"] > 38
    assert last["duration"] == "ok" and out["estimated_total_sec"] <= 30
    assert any(isinstance(v["rules"], list) and "UNSUPPORTED_EFFECT_CLAIM" in v["rules"]
               for v in out["revision_history"])
    final_text = json.dumps({"title": out["title"], "shots": out["shots"]}, ensure_ascii=False)
    assert "80" not in final_text
    assert {m["id"] for m in out["sources"]} == {"P01"}


def test_no_material_asks_after_rewrite(outputs):
    out = outputs["04_no_material"]
    assert len(out["retrieval"]["queries"]) == 2 and all(q["count"] == 0 for q in out["retrieval"]["queries"])
    assert out["shots"] == []  # 没有素材就不产出脚本


def test_rewrite_path_differs_from_no_material_path(outputs):
    """同样是首次检索 0 条：一个改写后命中继续写稿，一个改写后仍为空转为请求补充。"""
    rewrite = outputs["05_query_rewrite"]["retrieval"]["queries"]
    assert rewrite[0]["count"] == 0 and rewrite[1]["count"] > 0
    assert rewrite[1]["product"] == "帧跃 M2 无线麦克风"


def test_missing_info_then_answer_continues(outputs):
    out = outputs["03b_missing_info_answered"]
    assert out["brief_initial"]["target_duration_sec"] is None
    assert out["brief_final"]["platform"] == "抖音" and out["brief_final"]["target_duration_sec"] == 20


def test_infeasible_duration_reports_conflict(outputs):
    out = outputs["08_overtime_infeasible"]
    assert out["estimated_total_sec"] > out["target_duration_sec"]
    assert out["failure"]["suggestions"]


def test_rule_violation_fixed_and_logged(outputs):
    out = outputs["09_rule_violation"]
    assert any(isinstance(v["rules"], list) and "BANNED_WORD" in v["rules"] for v in out["revision_history"])
    assert "全网" not in json.dumps(out["shots"], ensure_ascii=False)
    assert any("极限词" in r for r in out["risks"])


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="设置 RUN_LIVE=1 且配置 DEEPSEEK_API_KEY 后运行")
def test_live_deepseek_reference_case(store, rules):
    from vsagent.config import load_env
    load_env()
    out = run_case(load_case(INPUTS / "02_reference_p01.json"), "deepseek", None)
    assert out["status"] in ("completed", "failed")
    assert verify_output(out, store, rules) == []
    assert "80%" not in json.dumps(out["shots"], ensure_ascii=False)
