"""三个业务工具的单元测试：素材检索、时长估算、规则检查。"""
import pytest

from conftest import shot

from vsagent.schema import Brief, normalize_script
from vsagent.tools import RuleChecker
from vsagent.tools import duration as duration_tool
from vsagent.tools.rules import extract_numbers


# ---------------- 素材检索 ----------------
def test_search_by_product_returns_only_that_product(store):
    res = store.search("帧跃剪辑 字幕", product="帧跃剪辑 App")
    assert [m["id"] for m in res["items"]] == ["P01"]


def test_search_unknown_product_is_empty_with_hint(store):
    res = store.search("帧跃 X1 智能云台 卖点", product="帧跃 X1 智能云台")
    assert res["count"] == 0
    assert "帧跃 M2 无线麦克风" in res["known_products"]


def test_search_typo_product_fails_then_rewrite_succeeds(store):
    assert store.search("帧越 M2 领夹麦", product="帧越 M2 领夹麦")["count"] == 0
    res = store.search("帧跃 M2 卖点", product="帧跃 M2 无线麦克风")
    assert {"M01", "M02", "M03", "M04", "M05", "M06"} <= {m["id"] for m in res["items"]}


def test_search_by_keyword_without_product(store):
    res = store.search("续航多久")
    assert res["items"][0]["id"] == "M02"


def test_brand_name_alone_is_not_relevant(store):
    assert store.search("帧跃")["count"] == 0


# ---------------- 时长估算 ----------------
def _est(shots, target=30, style="干货讲解", rules=None):
    return duration_tool.estimate(normalize_script({"title": "t", "shots": shots}), target, style,
                                  rules["duration_policy"])


def test_duration_sums_per_shot_and_flags_over(rules):
    long_line = "帧跃剪辑支持自动生成字幕，生成后可以逐句修改。" * 3
    res = _est([shot(long_line), shot(long_line)], target=20, rules=rules)
    assert res["status"] == "over" and not res["passed"]
    assert abs(sum(s["sec"] for s in res["per_shot"]) - res["total_sec"]) < 0.05
    assert "删减" in res["suggestion"]


def test_duration_under_and_ok(rules):
    res = _est([shot("你好。")], target=30, rules=rules)
    assert res["status"] == "under" and "不得为凑时长编造事实" in res["suggestion"]
    ok = _est([shot("", hold_sec=9.0, subtitle="演示")], target=10, rules=rules)
    assert ok["passed"] and ok["allowed_range_sec"] == [8.0, 10.0]


def test_hold_sec_and_style_speed(rules):
    res = _est([shot("", hold_sec=4.0, subtitle="演示")], rules=rules)
    assert res["per_shot"][0]["sec"] == 4.0
    fast = _est([shot("一二三四五六七八九十" * 2)], style="快节奏", rules=rules)
    slow = _est([shot("一二三四五六七八九十" * 2)], style="治愈舒缓", rules=rules)
    assert fast["total_sec"] < slow["total_sec"]


def test_numbers_count_as_spoken_syllables():
    assert duration_tool.speech_units("399元") > duration_tool.speech_units("9元")


# ---------------- 规则检查 ----------------
def _check(store, rules, brief, shots, retrieved_ids, title="帧跃剪辑字幕教程"):
    script = normalize_script({"title": title, "shots": shots})
    checker = RuleChecker(rules, store.brand)
    product = store.resolve_product(brief.product)
    return checker.check(script, brief, {i: store.by_id[i] for i in retrieved_ids}, set(store.by_id),
                         product["product_id"] if product else None)


def codes(result):
    return {v["code"] for v in result["violations"]}


def test_reference_case_efficiency_80_is_rejected(store, rules, editor_brief):
    """题目要求：只有 P01（支持字幕）时，不得写“效率提升80%”。"""
    res = _check(store, rules, editor_brief,
                 [shot("帧跃剪辑支持自动生成字幕，效率提升80%！", ["P01"])], ["P01"])
    assert {"UNSUPPORTED_NUMBER", "UNSUPPORTED_EFFECT_CLAIM"} <= codes(res)


def test_chinese_numeral_effect_claim_rejected(store, rules, editor_brief):
    res = _check(store, rules, editor_brief, [shot("帧跃剪辑自动字幕，剪辑时间缩短八成。", ["P01"])], ["P01"])
    assert "UNSUPPORTED_NUMBER" in codes(res)


def test_intensified_claim_rejected_and_plain_claim_warns(store, rules, editor_brief):
    res = _check(store, rules, editor_brief, [shot("帧跃剪辑让效率大幅提升。", ["P01"])], ["P01"])
    assert "UNSUPPORTED_EFFECT_CLAIM" in codes(res)
    res2 = _check(store, rules, editor_brief, [shot("帧跃剪辑自动加字幕，帮你提升效率。", ["P01"])], ["P01"])
    assert res2["passed"]
    assert {w["code"] for w in res2["warnings"]} == {"EFFECT_CLAIM_NEEDS_REVIEW"}


def test_supported_script_passes(store, rules, editor_brief):
    res = _check(store, rules, editor_brief,
                 [shot("口播视频还在手动打字幕？"),
                  shot("帧跃剪辑能识别普通话，自动生成字幕，还能逐句修改。", ["P01"])], ["P01"])
    assert res["passed"], res["violations"]
    # 痛点提问里提到“字幕”不算产品宣称，只给提示
    assert {w["code"] for w in res["warnings"]} == {"FEATURE_MENTION_NO_SOURCE"}


def test_feature_not_in_source_is_rejected(store, rules, editor_brief):
    res = _check(store, rules, editor_brief, [shot("帧跃剪辑支持字幕和多语言翻译。", ["P01"])], ["P01"])
    assert "UNSUPPORTED_FEATURE" in codes(res)


def test_feature_without_source_and_unretrieved_source(store, rules, editor_brief):
    res = _check(store, rules, editor_brief, [shot("帧跃剪辑自动生成字幕。", [])], ["P01"])
    assert "MISSING_SOURCE" in codes(res)
    res_claim = _check(store, rules, editor_brief, [shot("一键就能生成字幕。", [])], ["P01"])
    assert "MISSING_SOURCE" in codes(res_claim)
    res2 = _check(store, rules, editor_brief, [shot("帧跃剪辑自动生成字幕。", ["P01", "M99"])], [])
    assert codes(res2) >= {"UNKNOWN_SOURCE"}
    assert len([v for v in res2["violations"] if v["code"] == "UNKNOWN_SOURCE"]) == 2


def test_disclaimer_banned_words_brand_title(store, rules, m2_brief):
    shots = [shot("全网最强收音神器！", []), shot("M2 续航约 8 小时。", ["M02"])]
    res = _check(store, rules, m2_brief, shots, ["M02"], title="帧越M2" + "很长" * 20)
    assert {"BANNED_WORD", "MISSING_DISCLAIMER", "MISSING_BRAND_MENTION", "TITLE_TOO_LONG",
            "WRONG_BRAND_NAME"} <= codes(res)
    fixed = [shot("这个收音神器你见过吗？"),
             shot("帧跃 M2 续航约 8 小时。", ["M02"], screen_note=store.by_id["M02"]["required_disclaimer"])]
    assert _check(store, rules, m2_brief, fixed, ["M02"], title="帧跃M2续航实测")["passed"]


def test_effect_data_supports_numbers(store, rules, m2_brief):
    res = _check(store, rules, m2_brief,
                 [shot("帧跃 M2 开降噪后，清晰度评分从 3.1 提升到 4.3 分。", ["M04"],
                       screen_note=store.by_id["M04"]["required_disclaimer"])],
                 ["M04"], title="帧跃M2降噪")
    assert res["passed"], res["violations"]


@pytest.mark.parametrize("claim", [
    "续航约 8 分钟", "续航约八分钟", "续航八天", "续航八", "充电需要 8 小时", "接收器提供 8 小时续航",
])
def test_battery_life_requires_matching_metric_and_unit(store, rules, m2_brief, claim):
    note = "发射器单次充满后在实验室关闭降噪连续录音，实际以使用环境为准"
    result = _check(store, rules, m2_brief, [shot(f"帧跃 M2 {claim}。", ["M02"], screen_note=note)],
                    ["M02"], title="帧跃 M2 续航")
    assert "UNSUPPORTED_QUANTIFIED_CLAIM" in codes(result)


@pytest.mark.parametrize("note", [
    "发射器单次充满后在实验室连续录音，实际以使用环境为准",
    "发射器单次充满后在实验室开启降噪连续录音，实际以使用环境为准",
    "发射器单次充满后并非在实验室，关闭降噪连续录音",
])
def test_battery_life_requires_applicable_conditions(store, rules, m2_brief, note):
    other = shot("接下来展示配件。", screen_note="发射器单次充满，实验室条件，关闭降噪连续录音")
    result = _check(store, rules, m2_brief, [
        shot("帧跃 M2 发射器续航约 8 小时。", ["M02"], screen_note=note), other,
    ], ["M02"], title="帧跃 M2 续航")
    assert "UNSUPPORTED_FACT_CONDITIONS" in codes(result)


def test_supported_battery_life_passes_and_wrong_subtitle_is_rejected(store, rules, m2_brief):
    note = "单次充满后在实验室关闭降噪连续录音，实际以使用环境为准"
    correct = shot("帧跃 M2 发射器续航约八小时。", ["M02"], subtitle="续航约 8 小时", screen_note=note)
    result = _check(store, rules, m2_brief, [correct], ["M02"], title="帧跃 M2 续航")
    assert result["passed"], result["violations"]
    wrong_subtitle = {**correct, "subtitle": "续航约 8 分钟"}
    result = _check(store, rules, m2_brief, [wrong_subtitle], ["M02"], title="帧跃 M2 续航")
    assert "UNSUPPORTED_QUANTIFIED_CLAIM" in codes(result)


def test_joint_citations_cannot_swap_metric_values(store, rules, m2_brief):
    result = _check(store, rules, m2_brief, [
        shot("帧跃 M2 发射器续航 50 小时，传输距离 8 米。", ["M02", "M03"],
             screen_note="单次充满后在实验室关闭降噪连续录音，传输距离为空旷无遮挡环境测试值"),
    ], ["M02", "M03"], title="帧跃 M2 收音")
    assert "UNSUPPORTED_QUANTIFIED_CLAIM" in codes(result)


def test_quantified_claim_requires_a_source_for_the_requested_product(store, rules, editor_brief):
    result = _check(store, rules, editor_brief, [
        shot("帧跃剪辑续航约 8 小时。", ["M02"], screen_note=store.by_id["M02"]["required_disclaimer"]),
    ], ["M02"], title="帧跃剪辑")
    assert "UNSUPPORTED_QUANTIFIED_CLAIM" in codes(result)


def test_effect_data_does_not_support_reversed_scores(store, rules, m2_brief):
    result = _check(store, rules, m2_brief, [
        shot("帧跃 M2 人声清晰度评分由 4.3 分升至 3.1 分。", ["M04"],
             screen_note="内部测试：20 名测试者，约 65dB 咖啡馆环境，开启 AI 降噪，5 分制"),
    ], ["M04"], title="帧跃 M2 降噪")
    assert "UNSUPPORTED_QUANTIFIED_CLAIM" in codes(result)


def test_title_cannot_borrow_conditions_from_a_shot(store, rules, m2_brief):
    result = _check(store, rules, m2_brief, [
        shot("帧跃 M2 发射器续航约 8 小时。", ["M02"],
             screen_note="单次充满后在实验室关闭降噪连续录音"),
    ], ["M02"], title="帧跃 M2 发射器续航 8 小时")
    assert any(v["code"] == "UNSUPPORTED_FACT_CONDITIONS" and v["where"] == "title" for v in result["violations"])


def test_launch_price_uses_same_currency_and_promotion_terms(store, rules, m2_brief):
    note = store.by_id["M06"]["required_disclaimer"]
    title = "帧跃 M2 上新"
    valid = _check(store, rules, m2_brief, [shot("帧跃 M2 首发价 399 元。", ["M06"], screen_note=note)],
                   ["M06"], title=title)
    assert valid["passed"], valid["violations"]
    wrong_currency = _check(store, rules, m2_brief, [shot("帧跃 M2 首发价 399 美元。", ["M06"], screen_note=note)],
                            ["M06"], title=title)
    assert "UNSUPPORTED_QUANTIFIED_CLAIM" in codes(wrong_currency)
    wrong_dates = _check(store, rules, m2_brief, [
        shot("帧跃 M2 首发价 399 元。", ["M06"], screen_note=note.replace("2026-11-20", "2026-11-30")),
    ], ["M06"], title=title)
    assert "UNSUPPORTED_FACT_CONDITIONS" in codes(wrong_dates)


def test_must_include_points(store, rules):
    brief = Brief.from_dict({"product": "帧跃 M2 无线麦克风", "platform": "抖音", "target_duration_sec": 10,
                             "must_include": ["降噪", "399"]})
    res = _check(store, rules, brief, [shot("帧跃 M2 支持 AI 降噪。", ["M01"])], ["M01"], title="帧跃M2")
    assert "MISSING_REQUIRED_POINT" in codes(res)


def test_first_step_is_not_banned(store, rules, editor_brief):
    res = _check(store, rules, editor_brief, [shot("第一步，打开帧跃剪辑。")], [])
    assert "BANNED_WORD" not in codes(res)


def test_extract_numbers():
    assert extract_numbers("提升80%，缩短八成，翻了两倍，M2，3.1分") == {80.0, 8.0, 2.0, 3.1}


def test_long_subtitle_needs_reading_time(rules):
    """真实运行发现：模型把卖点挪进长字幕、只留极短口播来压时长。字幕阅读时间也要计入。"""
    short = _est([shot("帧跃M2。")], rules=rules)
    long_sub = _est([shot("帧跃M2。", subtitle="AI降噪｜续航约8小时｜传输距离约50米｜Type-C与Lightning双接口｜首发价399元")],
                    rules=rules)
    assert long_sub["total_sec"] > short["total_sec"] + 3
    assert "字幕" in long_sub["per_shot"][0]["basis"]


def test_must_include_only_in_screen_note_is_not_enough(store, rules):
    brief = Brief.from_dict({"product": "帧跃 M2 无线麦克风", "platform": "抖音", "target_duration_sec": 10,
                             "must_include": ["399"]})
    res = _check(store, rules, brief, [shot("帧跃 M2 上新了。", ["M06"], screen_note="首发价399元，价格以官方页面为准")],
                 ["M06"], title="帧跃M2")
    assert "MISSING_REQUIRED_POINT" in codes(res)


def test_narration_budget_hint(rules):
    hint = duration_tool.narration_budget(30, "轻松种草", rules["duration_policy"])
    assert "27.0s" in hint and "110 字" in hint
    assert duration_tool.narration_budget(None, None, rules["duration_policy"]) is None


def test_over_duration_gives_per_shot_cut_plan(rules):
    """真实运行发现：只说“约需删减 17 字”时模型常常只删 2 字；给出逐镜删减建议。"""
    res = _est([shot("开头一句很短的话。"), shot("这是第二个镜头里一段相当长的旁白内容，用来说明某个功能的具体使用场景和细节。" * 2),
                shot("第三个镜头的旁白也比较长，继续展开说明这个功能能带来什么。")], target=15, rules=rules)
    assert res["status"] == "over"
    plan = res["cut_plan"]
    assert plan and plan[0]["shot_id"] == 2            # 最长的镜头删得最多
    assert sum(p["cut_chars"] for p in plan) >= 1
    assert "镜头2删约" in res["suggestion"]


def test_must_include_only_in_title_is_not_enough(store, rules):
    brief = Brief.from_dict({"product": "帧跃 M2 无线麦克风", "platform": "抖音", "target_duration_sec": 10,
                             "must_include": ["399"]})
    res = _check(store, rules, brief, [shot("帧跃 M2 上新了。", ["M06"], screen_note="价格以官方页面为准")],
                 ["M06"], title="帧跃M2首发399元")
    assert "MISSING_REQUIRED_POINT" in codes(res)
