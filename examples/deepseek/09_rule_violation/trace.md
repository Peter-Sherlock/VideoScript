# 运行记录：09_rule_violation（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 收音 降噪 续航", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M04', 'M05', 'M06'] | 简报指定产品为帧跃 M2，先检索其可用事实素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 143, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v1"}} | v1：6 镜，预计 31.3s，目标区间 [20.0, 25.0]s → 超时 | 素材齐全，先按 25 秒目标估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 114, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v2"}} | v2：6 镜，预计 25.1s，目标区间 [20.0, 25.0]s → 超时 | 按 cut_plan 一次删减约 40 字，压到建议的 22.5s | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 101, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v3"}} | v3：6 镜，预计 22.8s，目标区间 [20.0, 25.0]s → 通过 | 仍超 0.1s，按建议再删约 12 字留出余量 | check_rules |
| 5 | `check_rules` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 101, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v3"}} | v3：3 项违规 ['BANNED_WORD', 'TITLE_TOO_LONG'] | v3 时长已通过，接着检查事实溯源、品牌与必含要点 | estimate_duration |
| 6 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 103, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v4"}} | v4：6 镜，预计 23.3s，目标区间 [20.0, 25.0]s → 通过 | 按违规项去掉极限词并缩短标题，需重新估算时长 | check_rules |
| 7 | `check_rules` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 103, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v4"}} | v4：规则检查通过（提示 0 条） | v4 时长通过，复查极限词与标题长度是否已修复 | submit_script |
| 8 | `submit_script` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 103, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v4"}, "risks"… | v4 提交成功（23.3s，规则通过） | v4 已通过 estimate_duration 与 check_rules，提交最终稿 | 结束（completed） |

**结束状态：`completed`** — 脚本 v4 已通过时长与规则检查
（决策轮数 8，工具调用 8 次）
