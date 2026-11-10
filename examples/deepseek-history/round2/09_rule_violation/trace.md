# 运行记录：09_rule_violation（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 卖点 参数", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 需要先确认素材库中该产品的可用事实，避免编造 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2 实测", "shots": 7, "narration_chars": 167, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v1"}} | v1：7 镜，预计 36.7s，目标区间 [20.0, 25.0]s → 超时 | 素材含降噪、测试数据、接口、距离、价格，先按 25 秒目标估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 116, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v2"}} | v2：6 镜，预计 25.3s，目标区间 [20.0, 25.0]s → 超时 | v1 超时 11.7s，按建议压到约 22.5s：合并镜头、精简旁白 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 114, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v3"}} | v3：6 镜，预计 24.8s，目标区间 [20.0, 25.0]s → 通过 | v2 仅超 0.3s，按建议再删约 13 字留余量 | check_rules |
| 5 | `check_rules` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 114, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v3"}} | v3：3 项违规 ['BANNED_WORD', 'UNSUPPORTED_NUMBER'] | v3 时长 24.8s 已达标，接着检查事实溯源、品牌与必含要点 | check_rules |
| 6 | `check_rules` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 116, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v4"}} | v4：规则检查通过（提示 0 条） | 按违规项修正：日期改为素材原文，开头极限词改为客观表述 | estimate_duration |
| 7 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 116, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v4"}} | v4：6 镜，预计 25.3s，目标区间 [20.0, 25.0]s → 超时 | v4 规则已通过，但旁白有改动，需重新估算时长确认达标 | estimate_duration |
| 8 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 114, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v5"}} | v5：6 镜，预计 24.8s，目标区间 [20.0, 25.0]s → 通过 | v4 超 0.3s，精简开头旁白后重新估算 | check_rules |
| 9 | `check_rules` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 114, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v5"}} | v5：规则检查通过（提示 0 条） | v5 时长已达标，旁白有改动需重新做规则检查 | submit_script |
| 10 | `submit_script` | {"script": {"title": "咖啡馆录口播也清楚｜帧跃 M2", "shots": 6, "narration_chars": 114, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v5"}, "risks": ["用户要求开头必须用“… | v5 提交成功（24.8s，规则通过） | v5 同一版本已通过 estimate_duration（24.8s）与 check_rules（0 违规），可提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v5 已通过时长与规则检查
（决策轮数 10，工具调用 10 次）
