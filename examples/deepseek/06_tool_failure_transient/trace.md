# 运行记录：06_tool_failure_transient（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：{'search_materials': ['transient', 1]}；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 卖点 参数", "product": "帧跃 M2 无线麦克风"} | ❌ 失败：TIMEOUT（search_materials 调用超时（10s，注入故障）） | 简报指定产品为帧跃 M2，先检索其可用事实素材 | search_materials |
| 2 | `search_materials` | {"product": "帧跃 M2 无线麦克风", "query": "帧跃 M2 无线麦克风 卖点 参数"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 上次检索超时且可重试，重新检索帧跃 M2 素材 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 198, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v1"}} | v1：6 镜，预计 39.0s，目标区间 [24.0, 30.0]s → 超时 | 已拿到 6 条可用素材，先按 30 秒目标估算初稿时长 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 157, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v2"}} | v2：6 镜，预计 30.9s，目标区间 [24.0, 30.0]s → 超时 | v1 超时 9 秒，按 cut_plan 精简镜头 3/4/6 旁白后重新估算 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 147, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v3"}} | v3：6 镜，预计 28.7s，目标区间 [24.0, 30.0]s → 通过 | v2 仍超 0.9 秒，按 cut_plan 再精简镜头 2/3/4 旁白 | check_rules |
| 6 | `check_rules` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 147, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v3"}} | v3：1 项违规 ['BANNED_WORD'] | v3 时长已通过，提交同一版本做事实与平台规则检查 | estimate_duration |
| 7 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 143, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v4"}} | v4：6 镜，预计 27.8s，目标区间 [24.0, 30.0]s → 通过 | v3 因“第一支”极限词违规，改掉该表述后重新估算时长 | check_rules |
| 8 | `check_rules` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 143, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v4"}} | v4：规则检查通过（提示 0 条） | v4 时长已通过，重新检查极限词是否已消除 | submit_script |
| 9 | `submit_script` | {"script": {"title": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "shots": 6, "narration_chars": 143, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v4"},… | v4 提交成功（27.8s，规则通过） | v4 已同时通过时长（27.8s）与规则检查，提交同一版本 | 结束（completed） |

**结束状态：`completed`** — 脚本 v4 已通过时长与规则检查
（决策轮数 9，工具调用 9 次）
