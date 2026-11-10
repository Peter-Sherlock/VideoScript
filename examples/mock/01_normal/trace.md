# 运行记录：01_normal（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 vlog 新手收音避坑：帧跃 M2 无线麦克风", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 先按简报中的产品与主题检索素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑", "shots": 6, "narration_chars": 172, "source_ids": ["M01", "M02"], "version": "v1"}} | v1：6 镜，预计 40.8s，目标区间 [24.0, 30.0]s → 超时 | 检索到 6 条素材，写出初稿后先估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑", "shots": 5, "narration_chars": 99, "source_ids": ["M01", "M02"], "version": "v2"}} | v2：5 镜，预计 25.1s，目标区间 [24.0, 30.0]s → 通过 | 超出 10.8s，压缩后重新估算 | check_rules |
| 4 | `check_rules` | {"script": {"title": "vlog 新手收音避坑", "shots": 5, "narration_chars": 99, "source_ids": ["M01", "M02"], "version": "v2"}} | v2：1 项违规 ['MISSING_DISCLAIMER'] | v2 时长 25.1s 达标，进行规则检查 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑", "shots": 5, "narration_chars": 99, "source_ids": ["M01", "M02"], "version": "v3"}} | v3：5 镜，预计 25.1s，目标区间 [24.0, 30.0]s → 通过 | 按违规项 ['MISSING_DISCLAIMER'] 修改，修改后重新估算时长再检查 | check_rules |
| 6 | `check_rules` | {"script": {"title": "vlog 新手收音避坑", "shots": 5, "narration_chars": 99, "source_ids": ["M01", "M02"], "version": "v3"}} | v3：规则检查通过（提示 0 条） | v3 时长 25.1s 达标，进行规则检查 | submit_script |
| 7 | `submit_script` | {"script": {"title": "vlog 新手收音避坑", "shots": 5, "narration_chars": 99, "source_ids": ["M01", "M02"], "version": "v3"}, "risks": []} | v3 提交成功（25.1s，规则通过） | v3 时长与规则均通过，提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v3 已通过时长与规则检查
（决策轮数 7，工具调用 7 次）
