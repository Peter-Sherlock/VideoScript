# 运行记录：02b_reference_user_draft（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃剪辑 App 自动字幕 语音识别 普通话", "product": "帧跃剪辑 App"} | 命中 1 条 ['P01'] | 草稿引用了素材ID P01，需核实自动字幕功能事实是否可追溯 | search_materials |
| 1 | `search_materials` | {"query": "帧跃剪辑 字幕 效率 数据 效果", "product": "帧跃剪辑 App", "material_types": ["effect_data", "feature", "spec", "brand", "price"]} | 命中 1 条 ['P01'] | 草稿含“效率提升80%”效果结论，需查是否有effect_data支撑 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "口播加字幕别再一个字一个字敲了", "shots": 4, "narration_chars": 110, "source_ids": ["P01"], "version": "v1"}} | v1：4 镜，预计 26.5s，目标区间 [24.0, 30.0]s → 通过 | 素材仅P01功能事实、无效果数据，需删掉80%结论后测时长 | check_rules |
| 3 | `check_rules` | {"script": {"title": "口播加字幕别再一个字一个字敲了", "shots": 4, "narration_chars": 110, "source_ids": ["P01"], "version": "v1"}} | v1：规则检查通过（提示 1 条） | 时长26.5s落在24-30s区间，接着检查事实可追溯与平台规则 | submit_script |
| 4 | `submit_script` | {"script": {"title": "口播加字幕别再一个字一个字敲了", "shots": 4, "narration_chars": 110, "source_ids": ["P01"], "version": "v1"}, "risks": ["草稿中的“效率提升80%”无素材依据（素材库无 effect_… | v1 提交成功（26.5s，规则通过） | v1已通过时长估算(26.5s)与规则检查(0违规)，可提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v1 已通过时长与规则检查
（决策轮数 4，工具调用 5 次）
