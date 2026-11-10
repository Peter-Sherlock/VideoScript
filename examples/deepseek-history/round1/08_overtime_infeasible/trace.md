# 运行记录：08_overtime_infeasible（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 降噪 续航 传输距离 价格", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M03', 'M02', 'M01', 'M06', 'M04', 'M05'] | 简报字段齐全，先检索产品事实素材以支撑脚本 | estimate_duration |
| 2 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 75, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v1"}} | v1：5 镜，预计 15.5s，目标区间 [8.0, 10.0]s → 超时 | 素材已覆盖四个必含要点，先估算10秒快节奏脚本时长 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 57, "source_ids": ["M01", "M02", "M03", "M04", "M05", "M06"], "version": "v2"}} | v2：5 镜，预计 12.0s，目标区间 [8.0, 10.0]s → 超时 | v1超时5.5秒，按建议压缩旁白字数后重新估算 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 52, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "v3"}} | v3：5 镜，预计 11.0s，目标区间 [8.0, 10.0]s → 超时 | v2仍超2秒，再删约10字并精简开头钩子 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 51, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "v4"}} | v4：5 镜，预计 10.8s，目标区间 [8.0, 10.0]s → 超时 | v3超1秒，再删约5字旁白以落入8-10秒区间 | estimate_duration |
| 6 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 51, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "v4"}} | v4：5 镜，预计 10.8s，目标区间 [8.0, 10.0]s → 超时 | v4超0.8秒，再压缩开头钩子约4字 | estimate_duration |
| 7 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 49, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "v5"}} | v5：5 镜，预计 10.4s，目标区间 [8.0, 10.0]s → 超时 | 上版未实际改动，现真正删减开头与降噪镜头旁白各约2字 | estimate_duration |
| 8 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 49, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "v5"}} | v5：5 镜，预计 10.4s，目标区间 [8.0, 10.0]s → 超时 | v5超0.4秒，再删2字旁白即可落入区间 | estimate_duration |
| 9 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 47, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "v6"}} | v6：5 镜，预计 10.0s，目标区间 [8.0, 10.0]s → 通过 | 上版内容未变，现实际把开头改为“帧跃M2，十秒”并精简降噪句 | check_rules |
| 10 | `check_rules` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 47, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "v6"}} | v6：1 项违规 ['UNSUPPORTED_NUMBER'] | v6时长10.0秒已达标，现检查事实溯源、品牌与必含要点 | estimate_duration |
| 11 | `estimate_duration` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 49, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "new"}} | ❌ 拒绝：estimate_duration 达到单工具调用上限 | shot1“十秒”无素材依据，改为无数字钩子后重新估算时长 | check_rules |
| 12 | `check_rules` | {"script": {"title": "帧跃 M2 全卖点速览：399 元拿下", "shots": 5, "narration_chars": 49, "source_ids": ["M01", "M02", "M03", "M04", "M06"], "version": "v7"}} | v7：规则检查通过（提示 0 条） | 时长工具已达上限，先验证改后版本规则是否通过 | report_failure |
| 13 | `report_failure` | {"reason": "v7 已通过 check_rules（0 违规），但 estimate_duration 已达单工具 8 次调用上限，无法验证 v7 时长，按规则不能声称时长达标，故不提交。v6 曾实测 10.0 秒达标，但含无素材依据的数字“十秒”（UNSUPPORTED_NUMBER）；v7 仅把该句改为… | 明确失败：v7 已通过 check_rules（0 违规），但 estimate_duration 已达单工具 8 次调用上限，无 | v7规则已通过但时长无法验证，按硬性原则不提交，报告冲突并附最接近草稿 | 结束（failed） |

**结束状态：`failed`** — v7 已通过 check_rules（0 违规），但 estimate_duration 已达单工具 8 次调用上限，无法验证 v7 时长，按规则不能声称时长达标，故不提交。v6 曾实测 10.0 秒达标，但含无素材依据的数字“十秒”（UNSUPPORTED_NUMBER）；v7 仅把该句改为“帧跃 M2，卖点速览。”，字数由 6.5 音节变为 7 音节，预计总时长约 10.1 秒，略超 10 秒上限，需重新估算确认。
（决策轮数 13，工具调用 13 次）
