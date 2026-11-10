# 运行记录：05_query_rewrite（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧越 M2 领夹麦 卖点 参数", "product": "帧越 M2 领夹麦"} | 命中 0 条；product 参数“帧越 M2 领夹麦”未匹配任何产品（严格匹配名称/别名）。素材库现有产品：['帧跃剪辑 App', '帧跃 M2 无线麦克风'] | 简报指定产品为帧越 M2 领夹麦，需先获取可引用的事实素材 | search_materials |
| 2 | `search_materials` | {"product": "帧跃 M2 无线麦克风", "query": "帧跃 M2 无线麦克风 领夹 收音 卖点 参数"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 素材库提示正确产品名为“帧跃 M2 无线麦克风”，按此名重新检索 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "上班族口播收音，别再靠手机原声", "shots": 5, "narration_chars": 116, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v1"}} | v1：5 镜，预计 26.6s，目标区间 [16.0, 20.0]s → 超时 | 已有 M01-M06 事实素材，先按 20 秒目标写初版并估算时长 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "上班族口播收音，别再靠手机原声", "shots": 5, "narration_chars": 84, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v2"}} | v2：5 镜，预计 19.5s，目标区间 [16.0, 20.0]s → 通过 | v1 超时 6.6s，按 cut_plan 删减镜头2/3/5 旁白约 37 字后重新估算 | check_rules |
| 5 | `check_rules` | {"script": {"title": "上班族口播收音，别再靠手机原声", "shots": 5, "narration_chars": 84, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v2"}} | v2：规则检查通过（提示 0 条） | v2 时长 19.5s 已通过，接着检查事实可追溯、品牌与平台规则 | submit_script |
| 6 | `submit_script` | {"script": {"title": "上班族口播收音，别再靠手机原声", "shots": 5, "narration_chars": 84, "source_ids": ["M01", "M04", "M05", "M06"], "version": "v2"}, "risks": ["简报产品名写作“帧越 … | v2 提交成功（19.5s，规则通过） | v2 已通过时长估算（19.5s）与规则检查（0 违规），可提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v2 已通过时长与规则检查
（决策轮数 6，工具调用 6 次）
