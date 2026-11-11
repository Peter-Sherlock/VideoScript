"""Agent 循环与护栏：提交闸门、执行上限、故障注入、补充信息、非法参数。

用 ScriptedLLM（预设工具调用序列）驱动，验证的是代码护栏本身，与模型好坏无关。
"""
import json

import pytest
from conftest import ScriptedLLM, shot

from vsagent.agent import ScriptAgent
from vsagent.config import Limits
from vsagent.schema import Brief
from vsagent.tools import AnswerProvider, FaultPlan

GOOD = {"title": "帧跃剪辑自动字幕", "shots": [
    shot("口播视频还在一句句手动打字？"),
    shot("帧跃剪辑能识别普通话，自动生成字幕。", ["P01"]),
    shot("", ["P01"], subtitle="一键生成字幕演示", hold_sec=3.0),
    shot("生成后还能逐句手动修改，改错字很方便。", ["P01"]),
    shot("帧跃剪辑，评论区告诉我你最想剪什么视频。"),
]}
SEARCH = ("search_materials", {"query": "帧跃剪辑 字幕", "product": "帧跃剪辑 App"})


def make_agent(store, rules, steps, limits=None, faults=None, answers=None):
    return ScriptAgent(ScriptedLLM(steps), store, rules, limits or Limits(),
                       FaultPlan.parse(faults), AnswerProvider(answers))


def brief(**kw):
    base = {"topic": "自动字幕", "product": "帧跃剪辑 App", "platform": "视频号",
            "target_duration_sec": 25, "style": "干货讲解"}
    base.update(kw)
    return Brief.from_dict(base)


def test_happy_path_completed(store, rules):
    agent = make_agent(store, rules, [SEARCH, ("estimate_duration", {"script": GOOD}),
                                      ("check_rules", {"script": GOOD}),
                                      ("submit_script", {"script": GOOD, "risks": []})])
    out = agent.run(brief()).output
    assert out["status"] == "completed", out["status_reason"]
    assert out["sources"][0]["id"] == "P01"
    assert out["checks"]["duration"]["script_version"] == out["checks"]["rules"]["script_version"] == "v1"


def test_submit_without_checks_is_rejected(store, rules):
    agent = make_agent(store, rules, [SEARCH, ("submit_script", {"script": GOOD, "risks": []})],
                       limits=Limits(max_steps=2))
    res = agent.run(brief())
    calls = res.trace.tool_calls()
    assert calls[-1]["tool"] == "submit_script" and not calls[-1]["ok"]
    assert "VERIFICATION_REQUIRED" in res.messages[-1]["content"]
    assert res.output["status"] == "incomplete"


def test_submit_different_version_than_checked_is_rejected(store, rules):
    edited = {**GOOD, "title": "帧跃剪辑自动字幕（改）"}
    agent = make_agent(store, rules, [SEARCH, ("estimate_duration", {"script": GOOD}),
                                      ("check_rules", {"script": GOOD}),
                                      ("submit_script", {"script": edited, "risks": []})],
                       limits=Limits(max_steps=4))
    res = agent.run(brief())
    assert res.output["status"] == "incomplete"
    assert "v2" in res.trace.tool_calls()[-1]["result_summary"]


def test_citing_unretrieved_material_fails_rules(store, rules):
    agent = make_agent(store, rules, [("check_rules", {"script": GOOD})], limits=Limits(max_steps=1))
    res = agent.run(brief())
    assert "UNKNOWN_SOURCE" in res.trace.tool_calls()[0]["result_summary"]


def test_step_limit_returns_incomplete(store, rules):
    agent = make_agent(store, rules, [SEARCH] * 10, limits=Limits(max_steps=3))
    out = agent.run(brief()).output
    assert out["status"] == "incomplete" and "最大决策轮数上限 3" in out["status_reason"]
    assert out["run"]["steps_used"] == 3


def test_tool_call_limit_returns_incomplete(store, rules):
    agent = make_agent(store, rules, [[SEARCH, SEARCH, SEARCH]] * 3, limits=Limits(max_tool_calls=4))
    out = agent.run(brief()).output
    assert out["status"] == "incomplete" and "工具调用总上限 4" in out["status_reason"]
    assert out["run"]["tool_calls_used"] == 4


def test_per_tool_limit_is_reported_to_model(store, rules):
    llm_steps = [SEARCH] * 3
    agent = make_agent(store, rules, llm_steps, limits=Limits(max_steps=3, max_calls_per_tool=2))
    res = agent.run(brief())
    assert "TOOL_CALL_LIMIT" in res.messages[-1]["content"]


def test_transient_fault_is_observation_not_auto_retry(store, rules):
    agent = make_agent(store, rules, [SEARCH, SEARCH], limits=Limits(max_steps=2),
                       faults=["search_materials:transient:1"])
    res = agent.run(brief())
    calls = res.trace.tool_calls()
    assert [c["ok"] for c in calls] == [False, True]  # 第一次失败，模型决定重试后成功
    assert "TIMEOUT" in calls[0]["result_summary"]
    assert res.output["system_notes"][0].startswith("工具调用失败 1 次")


def test_permanent_fault_then_model_reports_failure(store, rules):
    steps = [SEARCH, ("estimate_duration", {"script": GOOD}), ("estimate_duration", {"script": GOOD}),
             ("report_failure", {"reason": "时长服务不可用", "suggestions": ["稍后重试"], "best_script": GOOD})]
    out = make_agent(store, rules, steps, faults=["estimate_duration:permanent"]).run(brief()).output
    assert out["status"] == "failed"
    assert out["failure"]["reason"] == "时长服务不可用"
    assert out["checks"]["duration"] is None  # 不能假装检查过


def test_missing_info_needs_input(store, rules):
    steps = [("request_user_input", {"questions": ["目标时长多少秒？"], "missing": ["target_duration_sec"]})]
    out = make_agent(store, rules, steps).run(brief(target_duration_sec=None)).output
    assert out["status"] == "needs_input" and out["questions"] == ["目标时长多少秒？"]


def test_estimate_without_target_returns_error(store, rules):
    agent = make_agent(store, rules, [SEARCH, ("estimate_duration", {"script": GOOD})], limits=Limits(max_steps=2))
    res = agent.run(brief(target_duration_sec=None))
    assert "MISSING_TARGET" in res.messages[-1]["content"]


def test_update_brief_requires_user_reply_and_cannot_override(store, rules):
    steps = [("update_brief", {"target_duration_sec": 60}),
             ("request_user_input", {"questions": ["时长？"]}),
             ("update_brief", {"target_duration_sec": 25, "platform": "抖音"})]
    res = make_agent(store, rules, steps, limits=Limits(max_steps=3), answers=["25 秒"]).run(
        brief(target_duration_sec=None))
    calls = res.trace.tool_calls()
    assert not calls[0]["ok"]                                  # 没有用户回复前不能改
    assert res.output["brief_final"]["target_duration_sec"] == 25.0
    assert res.output["brief_final"]["platform"] == "视频号"     # 用户已给定的字段不能被改


def test_text_only_turn_gets_nudged(store, rules):
    agent = make_agent(store, rules, [None, SEARCH], limits=Limits(max_steps=2))
    res = agent.run(brief())
    assert any(e["type"] == "nudge" for e in res.trace.events)
    assert res.trace.tool_calls()[0]["tool"] == "search_materials"


def test_invalid_arguments_and_unknown_tool(store, rules):
    agent = make_agent(store, rules, [("estimate_duration", {"script": {"title": "x", "shots": []}}),
                                      ("no_such_tool", {})], limits=Limits(max_steps=2))
    res = agent.run(brief())
    summaries = [c["result_summary"] for c in res.trace.tool_calls()]
    assert "脚本结构错误" in summaries[0] and "未知工具" in summaries[1]


def test_trace_records_next_action(store, rules):
    agent = make_agent(store, rules, [SEARCH, ("estimate_duration", {"script": GOOD}),
                                      ("check_rules", {"script": GOOD}),
                                      ("submit_script", {"script": GOOD, "risks": []})])
    calls = agent.run(brief()).trace.tool_calls()
    assert [c["next_action"] for c in calls] == ["estimate_duration", "check_rules", "submit_script",
                                                 "结束（completed）"]
    assert all(c["decision_reason"] == "test" for c in calls)


def test_resubmitting_same_version_is_flagged(store, rules):
    """真实运行发现模型会“声称已修改”但提交同一版本；工具不重算，返回 DUPLICATE_SUBMISSION 让模型决定。"""
    agent = make_agent(store, rules, [SEARCH, ("estimate_duration", {"script": GOOD}),
                                      ("estimate_duration", {"script": GOOD})], limits=Limits(max_steps=3))
    res = agent.run(brief())
    calls = res.trace.tool_calls()
    assert calls[1]["ok"] and not calls[2]["ok"]
    assert "未修改" in calls[2]["result_summary"]
    assert "DUPLICATE_SUBMISSION" in res.messages[-1]["content"]
    assert "report_failure" in res.messages[-1]["content"]


def test_duplicate_check_does_not_break_gate(store, rules):
    """估算 → 检查 → 再次估算同一版本（重复）→ 提交：闸门依据已有结果放行。"""
    steps = [SEARCH, ("estimate_duration", {"script": GOOD}), ("check_rules", {"script": GOOD}),
             ("estimate_duration", {"script": GOOD}), ("submit_script", {"script": GOOD, "risks": []})]
    assert make_agent(store, rules, steps).run(brief()).output["status"] == "completed"


def test_update_brief_rejects_values_not_in_user_reply(store, rules):
    """真实运行发现：用户没提风格，模型把自己假设的“快节奏带货”写进简报（风格会影响语速口径）。"""
    steps = [("request_user_input", {"questions": ["平台和时长？"]}),
             ("update_brief", {"platform": "抖音", "target_duration_sec": 20, "audience": "想做口播的上班族",
                               "style": "快节奏带货口播"})]
    res = make_agent(store, rules, steps, limits=Limits(max_steps=2),
                     answers=["发抖音，20 秒左右，面向想做口播的上班族"]).run(
        Brief.from_dict({"product": "帧跃 M2 无线麦克风"}))
    final = res.output["brief_final"]
    assert final["platform"] == "抖音" and final["target_duration_sec"] == 20.0
    assert final["audience"] == "想做口播的上班族"
    assert final["style"] is None
    assert "假设" in res.messages[-1]["content"]


@pytest.mark.parametrize(("field", "reply", "script", "target", "tool"), [
    ("platform", "小红书", {**GOOD, "title": GOOD["title"] * 3}, 25, "check_rules"),
    ("style", "慢节奏", GOOD, 22, "estimate_duration"),
])
def test_checks_expire_when_brief_changes(store, rules, field, reply, script, target, tool):
    check_args = {"script": script}
    steps = [SEARCH, ("estimate_duration", check_args), ("check_rules", check_args),
             ("request_user_input", {"questions": ["请补充信息"]}), ("update_brief", {field: reply}),
             ("submit_script", check_args), (tool, check_args)]
    res = make_agent(store, rules, steps, limits=Limits(max_steps=7), answers=[reply]).run(
        brief(target_duration_sec=target, **{field: None}))
    observations = [json.loads(m["content"]) for m in res.messages if m["role"] == "tool"]
    assert all(o["passed"] for o in observations[1:3])
    assert observations[5]["error_type"] == "VERIFICATION_REQUIRED"
    assert observations[6]["ok"] and not observations[6]["passed"]
    assert observations[6]["script_version"] == "v1"
    assert res.output["status"] == "incomplete"


def test_submit_requires_complete_brief(store, rules):
    args = {"script": GOOD}
    steps = [SEARCH, ("estimate_duration", args), ("check_rules", args), ("submit_script", args)]
    res = make_agent(store, rules, steps, limits=Limits(max_steps=4)).run(brief(platform=None))
    assert json.loads(res.messages[-1]["content"])["error_type"] == "MISSING_BRIEF"
    assert res.output["status"] == "incomplete"


def test_rule_check_can_be_repeated_after_retrieving_a_cited_source(store, rules):
    args = {"script": GOOD}
    steps = [("check_rules", args), SEARCH, ("check_rules", args),
             ("estimate_duration", args), ("submit_script", args)]
    res = make_agent(store, rules, steps, limits=Limits(max_steps=5)).run(brief())
    assert "UNKNOWN_SOURCE" in res.trace.tool_calls()[0]["result_summary"]
    assert res.output["status"] == "completed"
    assert res.output["script_version"] == "v1"


def test_battery_unit_mismatch_blocks_submission_until_corrected(store, rules):
    source = ("search_materials", {"query": "续航", "product": "帧跃 M2 无线麦克风"})
    good = shot("帧跃 M2 发射器续航约 8 小时。", ["M02"], hold_sec=22,
                screen_note="单次充满后在实验室关闭降噪连续录音")
    wrong = {**good, "narration": good["narration"].replace("小时", "分钟")}
    args = [{"script": {"title": "帧跃 M2 续航", "shots": [s]}} for s in (wrong, good)]
    steps = [source, *[(tool, arg) for arg in args for tool in
                        ("estimate_duration", "check_rules", "submit_script")]]
    res = make_agent(store, rules, steps, limits=Limits(max_steps=7)).run(brief(product="帧跃 M2 无线麦克风"))
    observations = [json.loads(m["content"]) for m in res.messages if m["role"] == "tool"]
    assert observations[1]["passed"]
    assert not observations[2]["passed"]
    assert observations[3]["error_type"] == "VERIFICATION_REQUIRED"
    assert res.output["status"] == "completed"
    assert res.output["script_version"] == "v2"
    assert res.output["shots"][0]["narration"] == good["narration"]


@pytest.mark.parametrize(("args", "error_type"), [
    ("[]", "INVALID_ARGUMENTS"),
    ("null", "INVALID_ARGUMENTS"),
    ({"script": {**GOOD, "shots": [{**GOOD["shots"][0], "source_ids": 1}]}}, "INVALID_SCRIPT"),
    ({"script": {**GOOD, "shots": [{**GOOD["shots"][0], "hold_sec": "Infinity"}]}}, "INVALID_SCRIPT"),
])
def test_bad_tool_payload_returns_observation_and_run_continues(store, rules, args, error_type):
    valid = {"script": GOOD}
    steps = [("estimate_duration", args), SEARCH, ("estimate_duration", valid),
             ("check_rules", valid), ("submit_script", valid)]
    res = make_agent(store, rules, steps, limits=Limits(max_steps=5)).run(brief())
    first_observation = next(m for m in res.messages if m["role"] == "tool")
    assert json.loads(first_observation["content"])["error_type"] == error_type
    assert res.output["status"] == "completed"


@pytest.mark.parametrize("reply", ["120 秒", "面向 20 岁的用户，时长 30 秒"])
def test_duration_update_requires_the_confirmed_number_of_seconds(store, rules, reply):
    steps = [("request_user_input", {"questions": ["多长？"]}), ("update_brief", {"target_duration_sec": 20})]
    res = make_agent(store, rules, steps, limits=Limits(max_steps=2), answers=[reply]).run(
        brief(target_duration_sec=None))
    assert res.output["brief_final"]["target_duration_sec"] is None
