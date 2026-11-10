# 运行记录：01_normal（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 降噪 功能 参数", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M04', 'M05', 'M06'] | 简报信息完整，先检索帧跃 M2 的功能与降噪素材作为事实依据 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 6, "narration_chars": 127, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v1"}} | v1：6 镜，预计 29.3s，目标区间 [24.0, 30.0]s → 通过 | 素材已获取，先按30秒目标出完整版本并估算时长 | check_rules |
| 3 | `check_rules` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 6, "narration_chars": 127, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v1"}} | v1：规则检查通过（提示 0 条） | 时长已达标，提交同一版本做事实与平台规则检查 | submit_script |
| 4 | `submit_script` | {"script": {"title": "vlog新手收音避坑：帧跃M2无线麦克风", "shots": 6, "narration_chars": 127, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v1"}, "risks": ["未使用续航… | v1 提交成功（29.3s，规则通过） | v1 已同时通过时长估算与规则检查，提交最终脚本 | 结束（completed） |

**结束状态：`completed`** — 脚本 v1 已通过时长与规则检查
（决策轮数 4，工具调用 4 次）
