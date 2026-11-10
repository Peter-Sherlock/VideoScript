# 运行记录：02b_reference_user_draft（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃剪辑 自动字幕 语音识别", "product": "帧跃剪辑 App"} | 命中 1 条 ['P01'] | 需核实草稿中自动字幕、普通话识别、逐句修改等说法是否有素材依据 | search_materials |
| 1 | `search_materials` | {"query": "帧跃剪辑 字幕 效率 效果数据", "product": "帧跃剪辑 App", "material_types": ["effect_data", "feature", "spec", "brand"]} | 命中 1 条 ['P01'] | 草稿写了“效率提升80%”，需查是否有对应效果数据支撑 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "口播加字幕，别再一个字一个字敲了", "shots": 4, "narration_chars": 104, "source_ids": ["P01"], "version": "v1"}} | v1：4 镜，预计 25.1s，目标区间 [24.0, 30.0]s → 通过 | 素材仅支持功能事实，先删掉80%效果说法并压缩到30秒内再估算 | check_rules |
| 3 | `check_rules` | {"script": {"title": "口播加字幕，别再一个字一个字敲了", "shots": 4, "narration_chars": 104, "source_ids": ["P01"], "version": "v1"}} | v1：规则检查通过（提示 1 条） | 时长已通过，需确认事实可追溯、品牌露出与平台规则 | submit_script |
| 4 | `submit_script` | {"script": {"title": "口播加字幕，别再一个字一个字敲了", "shots": 4, "narration_chars": 104, "source_ids": ["P01"], "version": "v1"}, "risks": ["草稿中的“效率提升80%”无素材依据，已删除；素材库仅有 P… | v1 提交成功（25.1s，规则通过） | v1 已通过时长（25.1s）与规则检查（0 违规），可提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v1 已通过时长与规则检查
（决策轮数 4，工具调用 5 次）
