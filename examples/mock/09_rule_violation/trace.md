# 运行记录：09_rule_violation（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 咖啡馆录口播也清楚", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M04', 'M01', 'M02', 'M03', 'M05', 'M06'] | 先按简报中的产品与主题检索素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚", "shots": 5, "narration_chars": 122, "source_ids": ["M01"], "version": "v1"}} | v1：5 镜，预计 30.2s，目标区间 [20.0, 25.0]s → 超时 | 检索到 6 条素材，写出初稿后先估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚", "shots": 4, "narration_chars": 71, "source_ids": ["M01"], "version": "v2"}} | v2：4 镜，预计 19.4s，目标区间 [20.0, 25.0]s → 过短 | 超出 5.2s，压缩后重新估算 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚", "shots": 4, "narration_chars": 71, "source_ids": ["M01"], "version": "v3"}} | v3：4 镜，预计 20.8s，目标区间 [20.0, 25.0]s → 通过 | 短了 0.6s，延长展示镜头后重新估算 | check_rules |
| 5 | `check_rules` | {"script": {"title": "咖啡馆录口播也清楚", "shots": 4, "narration_chars": 71, "source_ids": ["M01"], "version": "v3"}} | v3：2 项违规 ['BANNED_WORD'] | v3 时长 20.8s 达标，进行规则检查 | estimate_duration |
| 6 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚", "shots": 4, "narration_chars": 67, "source_ids": ["M01"], "version": "v4"}} | v4：4 镜，预计 19.9s，目标区间 [20.0, 25.0]s → 过短 | 按违规项 ['BANNED_WORD'] 修改，修改后重新估算时长再检查 | estimate_duration |
| 7 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚", "shots": 4, "narration_chars": 67, "source_ids": ["M01"], "version": "v5"}} | v5：4 镜，预计 20.7s，目标区间 [20.0, 25.0]s → 通过 | 短了 0.1s，延长展示镜头后重新估算 | check_rules |
| 8 | `check_rules` | {"script": {"title": "咖啡馆录口播也清楚", "shots": 4, "narration_chars": 67, "source_ids": ["M01"], "version": "v5"}} | v5：规则检查通过（提示 0 条） | v5 时长 20.7s 达标，进行规则检查 | submit_script |
| 9 | `submit_script` | {"script": {"title": "咖啡馆录口播也清楚", "shots": 4, "narration_chars": 67, "source_ids": ["M01"], "version": "v5"}, "risks": ["用户要求中的“全网”属于广告极限词，已删除", "用户要求中的“最强”属于广… | v5 提交成功（20.7s，规则通过） | v5 时长与规则均通过，提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v5 已通过时长与规则检查
（决策轮数 9，工具调用 9 次）
