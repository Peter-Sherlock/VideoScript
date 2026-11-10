# 运行记录：08_overtime_infeasible（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 帧跃 M2 3 秒贴片广告", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 先按简报中的产品与主题检索素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "帧跃 M2 3 秒贴片广告", "shots": 9, "narration_chars": 367, "source_ids": ["M01", "M02", "M03", "M05", "M06"], "version": "v1"}} | v1：9 镜，预计 73.0s，目标区间 [2.4, 3.0]s → 超时 | 检索到 6 条素材，写出初稿后先估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "帧跃 M2 3 秒贴片广告", "shots": 8, "narration_chars": 228, "source_ids": ["M01", "M02", "M03", "M05", "M06"], "version": "v2"}} | v2：8 镜，预计 45.3s，目标区间 [2.4, 3.0]s → 超时 | 超出 70.0s，压缩后重新估算 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "帧跃 M2 3 秒贴片广告", "shots": 8, "narration_chars": 167, "source_ids": ["M01", "M02", "M03", "M05", "M06"], "version": "v3"}} | v3：8 镜，预计 34.0s，目标区间 [2.4, 3.0]s → 超时 | 超出 42.3s，压缩后重新估算 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "帧跃 M2 3 秒贴片广告", "shots": 8, "narration_chars": 160, "source_ids": ["M01", "M02", "M03", "M05", "M06"], "version": "v4"}} | v4：8 镜，预计 30.7s，目标区间 [2.4, 3.0]s → 超时 | 超出 31.0s，压缩后重新估算 | report_failure |
| 6 | `report_failure` | {"reason": "在保留用户必含要点 ['降噪', '续航', '传输距离', '399', 'Type-C', 'Lightning', '首发价'] 的前提下，最短也需要 30.7s，超出允许区间 [2.4, 3.0]s，无法同时满足", "failed_checks": ["estimate_durati… | 明确失败：在保留用户必含要点 ['降噪', '续航', '传输距离', '399', 'Type-C', 'Lightning', | 已压缩到不能再删的程度仍超时，明确报告无法满足 | 结束（failed） |

**结束状态：`failed`** — 在保留用户必含要点 ['降噪', '续航', '传输距离', '399', 'Type-C', 'Lightning', '首发价'] 的前提下，最短也需要 30.7s，超出允许区间 [2.4, 3.0]s，无法同时满足
（决策轮数 6，工具调用 6 次）
