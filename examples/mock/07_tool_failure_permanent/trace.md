# 运行记录：07_tool_failure_permanent（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：{'estimate_duration': ['permanent', 1]}；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃剪辑 App 帧跃剪辑自动字幕", "product": "帧跃剪辑 App"} | 命中 1 条 ['P01'] | 先按简报中的产品与主题检索素材 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "帧跃剪辑自动字幕", "shots": 5, "narration_chars": 143, "source_ids": ["P01"], "version": "未登记(工具未执行)"}} | ❌ 失败：SERVICE_UNAVAILABLE（estimate_duration 服务暂不可用（HTTP 503，注入故障）） | 检索到 1 条素材，写出初稿后先估算时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "帧跃剪辑自动字幕", "shots": 5, "narration_chars": 143, "source_ids": ["P01"], "version": "未登记(工具未执行)"}} | ❌ 失败：SERVICE_UNAVAILABLE（estimate_duration 服务暂不可用（HTTP 503，注入故障）） | estimate_duration 返回 SERVICE_UNAVAILABLE（可重试），重试一次 | report_failure |
| 4 | `report_failure` | {"reason": "时长估算连续失败（SERVICE_UNAVAILABLE），无法完成必要的检查，不能交付未验证的脚本", "failed_checks": ["estimate_duration"], "suggestions": ["稍后重试", "或由人工核对时长/规则后再发布"], "best_scri… | 明确失败：时长估算连续失败（SERVICE_UNAVAILABLE），无法完成必要的检查，不能交付未验证的脚本 | estimate_duration 重试后仍失败，判断服务不可用，停止并说明 | 结束（failed） |

**结束状态：`failed`** — 时长估算连续失败（SERVICE_UNAVAILABLE），无法完成必要的检查，不能交付未验证的脚本
（决策轮数 4，工具调用 4 次）
