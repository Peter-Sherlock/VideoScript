# 运行记录：03_missing_info（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 卖点 参数", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 先确认素材库是否有该产品可用事实，再决定脚本内容 | request_user_input |
| 1 | `request_user_input` | {"questions": ["这条视频发在哪个平台？（如抖音/小红书/视频号/B站/淘宝逛逛）", "目标时长是多少秒？（如 30 秒、60 秒、90 秒）", "目标受众是谁？（如口播博主、探店达人、新手vlogger、直播带货主播）", "风格偏好？（如快节奏带货、专业测评、生活化vlog）"], "missi… | 任务暂停，等待用户回答 4 个问题 | 简报缺平台与目标时长等关键字段，不能猜测，需用户补充 | 结束（needs_input） |

**结束状态：`needs_input`** — 缺少必要信息/素材，已向用户提出补充请求
（决策轮数 1，工具调用 2 次）
