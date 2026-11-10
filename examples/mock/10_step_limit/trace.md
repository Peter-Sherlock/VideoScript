# 运行记录：10_step_limit（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 3, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 vlog 新手收音避坑", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 先按简报中的产品与主题检索素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑", "shots": 6, "narration_chars": 172, "source_ids": ["M01", "M02"], "version": "v1"}} | v1：6 镜，预计 40.8s，目标区间 [24.0, 30.0]s → 超时 | 检索到 6 条素材，写出初稿后先估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "vlog 新手收音避坑", "shots": 5, "narration_chars": 99, "source_ids": ["M01", "M02"], "version": "v2"}} | v2：5 镜，预计 25.1s，目标区间 [24.0, 30.0]s → 通过 | 超出 10.8s，压缩后重新估算 | 结束（incomplete） |
| 3 | （上限） | - | 达到最大决策轮数上限 3，任务未完成 | - | 结束 |

**结束状态：`incomplete`** — 达到最大决策轮数上限 3，任务未完成
（决策轮数 3，工具调用 3 次）
