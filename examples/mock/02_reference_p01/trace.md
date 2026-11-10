# 运行记录：02_reference_p01（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃剪辑 App 帧跃剪辑的自动字幕功能，帮剪辑新手提高效率", "product": "帧跃剪辑 App"} | 命中 1 条 ['P01'] | 先按简报中的产品与主题检索素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "帧跃剪辑的自动字幕功能", "shots": 5, "narration_chars": 143, "source_ids": ["P01"], "version": "v1"}} | v1：5 镜，预计 36.7s，目标区间 [24.0, 30.0]s → 超时 | 检索到 1 条素材，写出初稿后先估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "帧跃剪辑的自动字幕功能", "shots": 4, "narration_chars": 92, "source_ids": ["P01"], "version": "v2"}} | v2：4 镜，预计 25.1s，目标区间 [24.0, 30.0]s → 通过 | 超出 6.7s，压缩后重新估算 | check_rules |
| 4 | `check_rules` | {"script": {"title": "帧跃剪辑的自动字幕功能", "shots": 4, "narration_chars": 92, "source_ids": ["P01"], "version": "v2"}} | v2：规则检查通过（提示 0 条） | v2 时长 25.1s 达标，进行规则检查 | submit_script |
| 5 | `submit_script` | {"script": {"title": "帧跃剪辑的自动字幕功能", "shots": 4, "narration_chars": 92, "source_ids": ["P01"], "version": "v2"}, "risks": ["素材中没有效果数据，脚本只陈述功能，不含效果量化结论"]} | v2 提交成功（25.1s，规则通过） | v2 时长与规则均通过，提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v2 已通过时长与规则检查
（决策轮数 5，工具调用 5 次）
