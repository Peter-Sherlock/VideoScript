# 运行记录：battery_life_draft（deepseek/deepseek-flash）

- 模型：`deepseek/deepseek-flash`
- 执行上限：{'max_steps': 14, 'max_tool_calls': 24, 'max_calls_per_tool': 8}
- 故障注入：无；预置用户回答：无

| 步 | 动作 | 参数摘要 | 返回摘要 | 决策依据（模型给出） | 后续动作 |
|---|---|---|---|---|---|
| 1 | `search_materials` | {"query": "帧跃 M2 无线麦克风 续航", "product": "帧跃 M2 无线麦克风"} | 命中 6 条 ['M02', 'M01', 'M03', 'M05', 'M06', 'M04'] | 需核对原稿中“续航约8分钟”等事实是否有素材依据 | search_materials |
| 1 | `search_materials` | {"query": "帧跃 M2 续航 测试条件 电池", "product": "帧跃 M2 无线麦克风", "material_types": ["spec", "effect_data", "feature"]} | 命中 5 条 ['M02', 'M04', 'M01', 'M03', 'M05'] | 补充检索续航规格与测试条件类素材 | check_rules |
| 2 | `check_rules` | {"script": {"title": "帧跃 M2 续航实测", "shots": 1, "narration_chars": 18, "source_ids": ["M02"], "version": "v1"}} | v1：1 项违规 ['UNSUPPORTED_QUANTIFIED_CLAIM'] | 按用户要求先检查原稿事实与规则问题 | estimate_duration |
| 3 | `estimate_duration` | {"script": {"title": "帧跃 M2 续航实测", "shots": 4, "narration_chars": 84, "source_ids": ["M02"], "version": "v2"}} | v2：4 镜，预计 20.1s，目标区间 [16.0, 20.0]s → 超时 | 修正单位后先估算时长是否落在20秒区间 | estimate_duration |
| 4 | `estimate_duration` | {"script": {"title": "帧跃 M2 续航实测", "shots": 4, "narration_chars": 66, "source_ids": ["M02"], "version": "v3"}} | v3：4 镜，预计 15.7s，目标区间 [16.0, 20.0]s → 过短 | 按建议删减约9字，压到18秒区间中部 | estimate_duration |
| 5 | `estimate_duration` | {"script": {"title": "帧跃 M2 续航实测", "shots": 4, "narration_chars": 73, "source_ids": ["M02"], "version": "v4"}} | v4：4 镜，预计 17.3s，目标区间 [16.0, 20.0]s → 通过 | 低于下限0.3秒，补回有依据的条件表述并加展示停留 | check_rules |
| 6 | `check_rules` | {"script": {"title": "帧跃 M2 续航实测", "shots": 4, "narration_chars": 73, "source_ids": ["M02"], "version": "v4"}} | v4：1 项违规 ['UNSUPPORTED_QUANTIFIED_CLAIM'] | 时长已达标，检查事实、品牌、免责与必含要点 | estimate_duration |
| 7 | `estimate_duration` | {"script": {"title": "帧跃 M2 续航实测", "shots": 4, "narration_chars": 73, "source_ids": ["M02"], "version": "v5"}} | v5：4 镜，预计 17.3s，目标区间 [16.0, 20.0]s → 通过 | 删掉“一天”这一无依据数量表述后重新估算时长 | check_rules |
| 8 | `check_rules` | {"script": {"title": "帧跃 M2 续航实测", "shots": 4, "narration_chars": 73, "source_ids": ["M02"], "version": "v5"}} | v5：规则检查通过（提示 0 条） | 已删除无依据数量，重新检查规则是否全部通过 | submit_script |
| 9 | `submit_script` | {"script": {"title": "帧跃 M2 续航实测", "shots": 4, "narration_chars": 73, "source_ids": ["M02"], "version": "v5"}, "risks": ["原稿“续航约 8 分钟”与素材 M02（约 8 小时）不符，已按素材改为 … | v5 提交成功（17.3s，规则通过） | v5版本时长17.3秒达标且规则检查passed=true，可提交 | 结束（completed） |

**结束状态：`completed`** — 脚本 v5 已通过时长与规则检查
（决策轮数 9，工具调用 10 次）
