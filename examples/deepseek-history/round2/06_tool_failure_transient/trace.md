# 运行记录：06_tool_failure_transient（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：{'search_materials': ['transient', 1]}；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 卖点 参数", "product": "帧跃 M2 无线麦克风"} | ❌ 失败：TIMEOUT（search_materials 调用超时（10s，注入故障）） | 简报指定产品为帧跃 M2，先按产品名检索全部可用事实素材 | search_materials |
| 2 | `search_materials` | {"product": "帧跃 M2 无线麦克风", "query": "帧跃 M2 无线麦克风 卖点 参数"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 上次检索超时且标记 retryable，重试同一检索 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 175, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v1"}} | v1：7 镜，预计 37.9s，目标区间 [24.0, 30.0]s → 超时 | 已取得 6 条可用素材，先按 30 秒目标写初版并估算时长 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 156, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v2"}} | v2：7 镜，预计 34.5s，目标区间 [24.0, 30.0]s → 超时 | v1 超时 7.9s，按建议压到约 27s：合并前两镜并精简旁白 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 145, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v3"}} | v3：7 镜，预计 32.0s，目标区间 [24.0, 30.0]s → 超时 | v2 仍超 4.5s，合并镜头1、2并再精简约34字旁白 | estimate_duration |
| 6 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 137, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v4"}} | v4：7 镜，预计 30.3s，目标区间 [24.0, 30.0]s → 超时 | v3 仍超 2s，合并开头两镜并精简镜头4、7，目标约27s | estimate_duration |
| 7 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 6, "narration_chars": 137, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v5"}} | v5：6 镜，预计 30.0s，目标区间 [24.0, 30.0]s → 通过 | v4 仅超0.3s但需留余量，合并镜头1、2并精简镜头4，压到约27s | check_rules |
| 8 | `check_rules` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 6, "narration_chars": 137, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v5"}} | v5：规则检查通过（提示 0 条） | v5 时长已通过，接着检查事实可追溯、品牌与平台规则 | submit_script |
| 9 | `submit_script` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 6, "narration_chars": 137, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v5"}, "r… | v5 提交成功（30.0s，规则通过） | v5 已通过时长估算（30.0s）与规则检查（0违规），提交最终稿 | 结束（completed） |

**结束状态：`completed`** — 脚本 v5 已通过时长与规则检查
（决策轮数 9，工具调用 9 次）
