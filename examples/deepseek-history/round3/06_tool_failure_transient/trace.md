# 运行记录：06_tool_failure_transient（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：{'search_materials': ['transient', 1]}；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 卖点 参数", "product": "帧跃 M2 无线麦克风"} | ❌ 失败：TIMEOUT（search_materials 调用超时（10s，注入故障）） | 简报指定产品为帧跃 M2，先检索其可用事实素材 | search_materials |
| 2 | `search_materials` | {"product": "帧跃 M2 无线麦克风", "query": "帧跃 M2 无线麦克风 卖点 参数"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 上次检索超时且标记可重试，重新检索帧跃 M2 素材 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 8, "narration_chars": 204, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v1"}} | v1：8 镜，预计 40.8s，目标区间 [24.0, 30.0]s → 超时 | 已拿到 M01-M06 六条素材，先按 30 秒目标估算初稿时长 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 154, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v2"}} | v2：6 镜，预计 29.3s，目标区间 [24.0, 30.0]s → 通过 | v1 超时 10.8s，按建议压到约 27s，合并开头两镜并精简旁白 | check_rules |
| 5 | `check_rules` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 154, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v2"}} | v2：1 项违规 ['BANNED_WORD'] | v2 时长 29.3s 已达标，接着检查事实可追溯、品牌与平台规则 | estimate_duration |
| 6 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 154, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v3"}} | v3：6 镜，预计 29.3s，目标区间 [24.0, 30.0]s → 通过 | v2 仅因极限词“第一”违规，改掉该词后需重新估算时长 | check_rules |
| 7 | `check_rules` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 154, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v3"}} | v3：规则检查通过（提示 0 条） | v3 时长 29.3s 达标，重新检查极限词等规则是否已清除 | submit_script |
| 8 | `submit_script` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 154, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v3"},… | v3 提交成功（29.3s，规则通过） | v3 已通过时长估算（29.3s）与规则检查（0 违规），提交最终稿 | 结束（completed） |

**结束状态：`completed`** — 脚本 v3 已通过时长与规则检查
（决策轮数 8，工具调用 8 次）
