# 运行记录：09_rule_violation（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 收音 降噪 续航", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M04', 'M05', 'M06'] | 简报产品明确，先按产品名检索全部可用事实素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "全网最强收音神器？咖啡馆录口播也清楚", "shots": 6, "narration_chars": 129, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v1"}} | v1：6 镜，预计 28.2s，目标区间 [20.0, 25.0]s → 超时 | 素材已覆盖降噪、测试数据、接口、续航、价格，先按 25 秒目标估算 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "全网最强收音神器？咖啡馆录口播也清楚", "shots": 5, "narration_chars": 97, "source_ids": ["M01", "M02", "M04", "M05", "M06"], "version": "v2"}} | v2：5 镜，预计 21.6s，目标区间 [20.0, 25.0]s → 通过 | 按建议删减约 15 字并合并镜头 4、5，重新估算 | check_rules |
| 4 | `check_rules` | {"script": {"title": "全网最强收音神器？咖啡馆录口播也清楚", "shots": 5, "narration_chars": 97, "source_ids": ["M01", "M02", "M04", "M05", "M06"], "version": "v2"}} | v2：3 项违规 ['BANNED_WORD', 'MISSING_BRAND_MENTION'] | v2 时长已达标，接着检查事实溯源、品牌与必含要点规则 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "咖啡馆录口播也清楚，探店带上帧跃 M2", "shots": 5, "narration_chars": 98, "source_ids": ["M01", "M02", "M04", "M05", "M06"], "version": "v3"}} | v3：5 镜，预计 21.7s，目标区间 [20.0, 25.0]s → 通过 | 按违规项去掉极限词并补品牌名，改后需重新估算时长 | check_rules |
| 6 | `check_rules` | {"script": {"title": "咖啡馆录口播也清楚，探店带上帧跃 M2", "shots": 5, "narration_chars": 98, "source_ids": ["M01", "M02", "M04", "M05", "M06"], "version": "v3"}} | v3：规则检查通过（提示 0 条） | v3 时长达标，重新检查是否已清除极限词并露出品牌名 | submit_script |
| 7 | `submit_script` | {"script": {"title": "咖啡馆录口播也清楚，探店带上帧跃 M2", "shots": 5, "narration_chars": 98, "source_ids": ["M01", "M02", "M04", "M05", "M06"], "version": "v3"}, "risks": ["… | v3 提交成功（21.7s，规则通过） | v3 已通过 estimate_duration 与 check_rules（0 违规），提交最终稿 | 结束（completed） |

**结束状态：`completed`** — 脚本 v3 已通过时长与规则检查
（决策轮数 7，工具调用 7 次）
