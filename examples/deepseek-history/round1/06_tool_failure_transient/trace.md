# 运行记录：06_tool_failure_transient（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：{'search_materials': ['transient', 1]}；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 卖点 参数", "product": "帧跃 M2 无线麦克风"} | ❌ 失败：TIMEOUT（search_materials 调用超时（10s，注入故障）） | 简报产品明确，先按产品名严格检索可用事实素材 | search_materials |
| 2 | `search_materials` | {"product": "帧跃 M2 无线麦克风", "query": "帧跃 M2 无线麦克风 卖点 参数"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 上次检索超时且标记可重试，重试同一检索 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 168, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v1"}} | v1：7 镜，预计 38.8s，目标区间 [24.0, 30.0]s → 超时 | 已拿到 6 条可用素材，先按 30 秒目标估算初稿时长 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 141, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v2"}} | v2：7 镜，预计 32.8s，目标区间 [24.0, 30.0]s → 超时 | 初稿超时8.8秒，按建议删减约40字旁白并合并镜头 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 132, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v3"}} | v3：7 镜，预计 31.3s，目标区间 [24.0, 30.0]s → 超时 | v2仍超2.8秒，按建议再删约13字旁白 | estimate_duration |
| 6 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 129, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v4"}} | v4：7 镜，预计 30.6s，目标区间 [24.0, 30.0]s → 超时 | v3仍超1.3秒，再删约6字旁白 | estimate_duration |
| 7 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 128, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v5"}} | v5：7 镜，预计 30.3s，目标区间 [24.0, 30.0]s → 超时 | v4仅超0.6秒，微调第4镜旁白再省3字 | estimate_duration |
| 8 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 128, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v5"}} | v5：7 镜，预计 30.3s，目标区间 [24.0, 30.0]s → 超时 | v5仅超0.3秒，第1镜旁白再省2字 | estimate_duration |
| 9 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 128, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v5"}} | v5：7 镜，预计 30.3s，目标区间 [24.0, 30.0]s → 超时 | 上版第1镜旁白未改动，这次真正删短2字 | estimate_duration |
| 10 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 123, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v6"}} | v6：7 镜，预计 29.3s，目标区间 [24.0, 30.0]s → 通过 | 前两次第1镜旁白未生效，这次明确改为“拍vlog最崩的是声音全是底噪” | check_rules |
| 11 | `check_rules` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 123, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v6"}} | v6：规则检查通过（提示 0 条） | v6时长29.3秒已达标，接着检查事实溯源与平台规则 | submit_script |
| 12 | `submit_script` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 7, "narration_chars": 123, "source_ids": ["M01", "M03", "M04", "M05", "M06"], "version": "v6"}, "risks": … | v6 提交成功（29.3s，规则通过） | v6已通过时长估算（29.3秒）与规则检查（0违规），提交定稿 | 结束（completed） |

**结束状态：`completed`** — 脚本 v6 已通过时长与规则检查
（决策轮数 12，工具调用 12 次）
