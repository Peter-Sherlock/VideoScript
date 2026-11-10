# 运行记录：03_missing_info（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `request_user_input` | {"questions": ["准备发布在哪个平台（抖音/小红书/视频号/B站/快手）？", "目标时长是多少秒？"], "missing": ["platform", "target_duration_sec"]} | 任务暂停，等待用户回答 2 个问题 | 缺少关键字段 ['platform', 'target_duration_sec']，不能猜测，向用户确认 | 结束（needs_input） |

**结束状态：`needs_input`** — 缺少必要信息/素材，已向用户提出补充请求
（决策轮数 1，工具调用 1 次）
