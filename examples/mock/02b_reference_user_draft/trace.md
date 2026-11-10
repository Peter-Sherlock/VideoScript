# 运行记录：02b_reference_user_draft（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃剪辑 App 帧跃剪辑自动字幕功能", "product": "帧跃剪辑 App"} | 命中 1 条 ['P01'] | 先按简报中的产品与主题检索素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "帧跃剪辑自动字幕，效率提升80%", "shots": 5, "narration_chars": 162, "source_ids": ["P01"], "version": "v1"}} | v1：5 镜，预计 38.9s，目标区间 [24.0, 30.0]s → 超时 | 检索到 1 条素材，写出初稿后先估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "帧跃剪辑自动字幕，效率提升80%", "shots": 5, "narration_chars": 114, "source_ids": ["P01"], "version": "v2"}} | v2：5 镜，预计 27.9s，目标区间 [24.0, 30.0]s → 通过 | 超出 8.9s，压缩后重新估算 | check_rules |
| 4 | `check_rules` | {"script": {"title": "帧跃剪辑自动字幕，效率提升80%", "shots": 5, "narration_chars": 114, "source_ids": ["P01"], "version": "v2"}} | v2：4 项违规 ['MISSING_SOURCE', 'UNSUPPORTED_EFFECT_CLAIM', 'UNSUPPORTED_NUMBER'] | v2 时长 27.9s 达标，进行规则检查 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "帧跃剪辑 App", "shots": 5, "narration_chars": 94, "source_ids": ["P01"], "version": "v3"}} | v3：5 镜，预计 23.3s，目标区间 [24.0, 30.0]s → 过短 | 按违规项 ['MISSING_SOURCE', 'UNSUPPORTED_EFFECT_CLAIM', 'UNSUPPORTED_NUMBER'] 修改，修改后重新估算时长再检查 | estimate_duration |
| 6 | `estimate_duration` | {"script": {"title": "帧跃剪辑 App", "shots": 5, "narration_chars": 94, "source_ids": ["P01"], "version": "v4"}} | v4：5 镜，预计 24.7s，目标区间 [24.0, 30.0]s → 通过 | 短了 0.7s，延长展示镜头后重新估算 | check_rules |
| 7 | `check_rules` | {"script": {"title": "帧跃剪辑 App", "shots": 5, "narration_chars": 94, "source_ids": ["P01"], "version": "v4"}} | v4：规则检查通过（提示 1 条） | v4 时长 24.7s 达标，进行规则检查 | submit_script |
| 8 | `submit_script` | {"script": {"title": "帧跃剪辑 App", "shots": 5, "narration_chars": 94, "source_ids": ["P01"], "version": "v4"}, "risks": ["删除了无素材依据的表述（MISSING_SOURCE，shot 4）：出现数字… | v4 提交成功（24.7s，规则通过） | v4 时长与规则均通过，提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v4 已通过时长与规则检查
（决策轮数 8，工具调用 8 次）
