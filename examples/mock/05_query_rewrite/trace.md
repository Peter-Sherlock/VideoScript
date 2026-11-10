# 运行记录：05_query_rewrite（mock/rule-policy）

- 模型：`mock/rule-policy`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧越 M2 领夹麦 上班族口播收音", "product": "帧越 M2 领夹麦"} | 命中 0 条；product 参数“帧越 M2 领夹麦”未匹配任何产品（严格匹配名称/别名）。素材库现有产品：['帧跃剪辑 App', '帧跃 M2 无线麦克风'] | 先按简报中的产品与主题检索素材 | search_materials |
| 2 | `search_materials` | {"query": "帧跃 M2 无线麦克风 卖点", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M01', 'M02', 'M03', 'M05', 'M06', 'M04'] | 0 条结果，hint 中的“帧跃 M2 无线麦克风”与简报产品名高度相似，疑似写法不同，改写后重查 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "上班族口播收音", "shots": 5, "narration_chars": 132, "source_ids": ["M01"], "version": "v1"}} | v1：5 镜，预计 34.1s，目标区间 [16.0, 20.0]s → 超时 | 检索到 6 条素材，写出初稿后先估算时长 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "上班族口播收音", "shots": 4, "narration_chars": 81, "source_ids": ["M01"], "version": "v2"}} | v2：4 镜，预计 22.6s，目标区间 [16.0, 20.0]s → 超时 | 超出 14.1s，压缩后重新估算 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "上班族口播收音", "shots": 4, "narration_chars": 67, "source_ids": ["M01"], "version": "v3"}} | v3：4 镜，预计 19.4s，目标区间 [16.0, 20.0]s → 通过 | 超出 2.6s，压缩后重新估算 | check_rules |
| 6 | `check_rules` | {"script": {"title": "上班族口播收音", "shots": 4, "narration_chars": 67, "source_ids": ["M01"], "version": "v3"}} | v3：规则检查通过（提示 0 条） | v3 时长 19.4s 达标，进行规则检查 | submit_script |
| 7 | `submit_script` | {"script": {"title": "上班族口播收音", "shots": 4, "narration_chars": 67, "source_ids": ["M01"], "version": "v3"}, "risks": []} | v3 提交成功（19.4s，规则通过） | v3 时长与规则均通过，提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v3 已通过时长与规则检查
（决策轮数 7，工具调用 7 次）
