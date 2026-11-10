# DeepSeek 历史运行记录（改进前，保留作对比证据）

最终结果在 [../deepseek/](../deepseek/)。这里保存的是**改进前**代码的真实运行结果，用来说明每次改动的依据和效果。各目录结构与最终结果相同（`input.json` / `output.json` / `output.md` / `trace.jsonl` / `trace.md`），`input.json` 是当时实际使用的输入。

## round1：初版代码

与最终代码的差异：时长建议只说“超出上限 X 秒”；没有重复提交检测；没有写稿字数参考；字幕阅读时间不计入时长；用例 08 当时是“10 秒讲完 4 个要点”；用例 02b 还不存在。

| 用例 | 状态 | 轮数/工具调用 | 各版本预计时长(s) |
|---|---|---|---|
| 01_normal | completed | 12/12 | 44.4 → 33.4 → 30.6 → 30.4 → 30.2 → 30.0 → 30.0 |
| 02_reference_p01 | completed | 7/9 | 26.9 → 27.6 |
| 03_missing_info | needs_input | 1/2 | - |
| 03b_missing_info_answered | **failed** | 12/13 | 31.5 → 25.6 → 22.3 → 22.1 → 21.8 → 21.5（v6 重复提交 3 次后撞上单工具上限） |
| 04_no_material | needs_input | 3/3 | - |
| 05_query_rewrite | completed | 6/6 | 28.2 → 18.9 |
| 06_tool_failure_transient | completed | 12/12 | 38.8 → 32.8 → 31.3 → 30.6 → 30.3 → 29.3 |
| 07_tool_failure_permanent | failed | 6/6 | 未估算（服务持续 503） |
| 08（10 秒 4 要点版） | failed | 13/13 | 15.5 → 12.0 → 11.0 → 10.8 → 10.4 → 10.0 →（v7 撞上单工具上限） |
| 09_rule_violation | completed | 7/7 | 28.2 → 21.6 → 21.7 |
| 10_step_limit | incomplete | 3/4 | 48.2 → 32.3 |

发现的问题 → 改动：
- 模型每次只删 1–3 字、贴着上限反复估算（01、03b、06、08）→ 估算结果增加 `recommended_sec`（区间中部）与对应删减字数；提示词要求一次调整到位。
- 声称已修改、实际重复提交同一版本（03b、06、08）→ 估算/检查结果中提示“与 vN 完全相同”。
- 08 的“做不到”假设不成立（真实模型写出了 47 字、10.0s 的版本）→ 改为“5 秒讲完 6 个要点”。
- 增加用例 02b（用户自带约 38 秒、含“效率提升80%”的草稿），稳定覆盖题目参考实例的压缩路径。

## round2：加入上述改动后

| 用例 | 状态 | 轮数/工具调用 | 各版本预计时长(s) |
|---|---|---|---|
| 01_normal | completed | 4/4 | 29.3 |
| 02_reference_p01 | completed | 8/10 | 32.8 → 25.1 → 24.6 |
| 02b_reference_user_draft | completed | 4/5 | 27.2（模型先删改再估算） |
| 02b_reference_user_draft_rerun | completed | 7/8 | 38.9 → 22.5 → 26.8（模型先测量草稿再压缩） |
| 03_missing_info | needs_input | 1/2 | - |
| 03b_missing_info_answered | **completed** | 9/10 | 34.5 → 23.6 → 21.8 → 21.5 → 17.8 |
| 04_no_material | needs_input | 3/4 | - |
| 05_query_rewrite | completed | 6/6 | 35.4 → 18.5 |
| 06_tool_failure_transient | completed | 9/9 | 37.9 → 34.5 → 32.0 → 30.3 → 30.0 |
| 07_tool_failure_permanent | failed | 6/6 | 未估算 |
| 08_overtime_infeasible | failed | 11/12 | 11.9 → 8.4 → 6.6 → **v3 被原样重复提交 6 次**（工具已提示“未修改”）→ 单工具上限 |
| 08_overtime_infeasible_after_dedup_fix | failed | 11/11 | 11.1 → 8.7 → 7.9 → 6.5 → 6.1 → 6.1 → 5.6 → 重复 1 次被拒 → 明确失败 |
| 09_rule_violation | completed | 10/10 | 36.7 → 25.3 → 24.8 → 25.3 → 24.8 |
| 10_step_limit | incomplete | 3/3 | 43.9 → 34.4 |

效果：03b 从 failed 变为 completed；01 从 12 步降到 4 步，06 从 12 步降到 9 步。

仍存在的问题 → 改动（进入最终版）：
- 仅“提示未修改”不够，08 中模型仍原样重复提交 6 次 → 同一版本重复提交给同一工具时不再重算，返回 `DUPLICATE_SUBMISSION` 错误，并说明“要么实际修改，要么 report_failure”（`08_overtime_infeasible_after_dedup_fix` 是加入此改动后的运行：重复降到 1 次）。
- 在 `08_overtime_infeasible_after_dedup_fix` 中，模型把卖点挪进长字幕、只保留极短口播来压时长（5.6s）→ 每镜时长改为取“口播时间”和“字幕阅读时间”的较大值；必含要点必须出现在标题/旁白/字幕中，只写在角标小字里不算。
- 首稿普遍偏长（多数 34–38s 对 30s 目标）→ 首条消息给出“按当前语速约 N 字旁白”的写稿参考，补充目标时长后 `update_brief` 也会返回。

## round3：加入 DUPLICATE_SUBMISSION、字幕阅读时间、写稿字数参考之后

| 用例 | 状态 | 轮数/工具调用 | 各版本预计时长(s) | 重复提交 |
|---|---|---|---|---|
| 01_normal | completed | 5/5 | 31.1 → 28.6 | 0 |
| 02_reference_p01 | completed | 9/10 | 28.7 → 28.9 → 28.7（两轮规则修正） | 0 |
| 02b_reference_user_draft | completed | 7/8 | 34.7 → 23.0 → 24.6 | 0 |
| 02b_reference_user_draft_rerun | completed | 4/5 | 25.1 | 0 |
| 03_missing_info | needs_input | 1/2 | - | 0 |
| 03b_missing_info_answered | completed | 7/8 | 26.2 → 20.6 → 19.4 | 0 |
| 04_no_material | needs_input | 3/3 | - | 0 |
| 05_query_rewrite | completed | 6/6 | 26.5 → 19.7 | 0 |
| 06_tool_failure_transient | completed | 8/8 | 40.8 → 29.3 → 29.3 | 0 |
| 07_tool_failure_permanent | failed | 6/7 | 未估算 | 0 |
| 08_overtime_infeasible（5 秒 6 要点版） | failed | 13/13 | 8.8 → 7.5 → 7.4 → 6.9 → 6.5 → 6.4 → 5.3 → **4.8** →（v9 未能估算） | 0 |
| 09_rule_violation | **failed** | 11/11 | 34.0 → 27.7 → 26.2 → 25.7 → 25.5 → 25.1 →（单工具上限） | 2 |
| 10_step_limit | incomplete | 3/4 | 31.5 → 26.1 | 0 |

效果：首稿明显变短（01 首稿 31.1s，第一轮是 44.4s），01、03b、06 都在 2–3 版内达标；除 09 外重复提交降为 0。

仍存在的问题 → 改动（进入最终版）：
- 09：建议压到 22.5s、约删 17 字，模型每次只删 2 字（26.2 → 25.7 → 25.5 → 25.1），撞上单工具上限后明确失败 → 超时结果增加逐镜删减建议 `cut_plan`（如“镜头2删约5字、镜头3删约5字”）。
- 08：模型把 6 个要点全部放进字幕、口播只留品牌名，v8 估算 4.8s 落入 5 秒区间。说明“5 秒 6 要点”按工具口径其实**能**做到，用例假设又错了；另外标题也被算作“包含要点”，但标题是发布文案、不在画面里 → 必含要点只认旁白和字幕；用例改为“3 秒 7 要点”（要点原词直接拼成一行字幕也至少 3.5s）。

## round4：加入逐镜删减建议 cut_plan 之后（批量运行）

除下面 4 个目录外，round4 批量运行的其余结果就是最终结果（[../deepseek/](../deepseek/)）。这 4 个因为之后又改了输入或代码，用最终版本重跑过：

| 目录 | 当时结果 | 之后的改动 |
|---|---|---|
| `round4/02b_reference_user_draft`、`round4/02b_reference_user_draft_rerun` | 均 completed，但模型都先改写再估算（25.7s、26.5s），没有出现“先测出 38 秒再压缩” | 用例需求写明“先帮我测一下现在有多长”（真实用户常见说法；怎么改仍由模型决定）。最终两次都先测出 38.9s 再压缩 |
| `round4/08_overtime_infeasible` | 5 秒 6 要点版：failed（8.9 → 7.1 → … → 5.1s） | 用例改为 3 秒 7 要点；必含要点只认旁白/字幕 |
| `round4/03b_missing_info_answered` | completed，但模型把用户没提过的风格“快节奏带货口播”写进了简报（风格决定语速口径，会放宽时长检查） | `update_brief` 只接受能在用户回答中找到依据的值 |

round4 的整体效果：12 个用例状态全部符合预期，“重复估算同一版本”的次数为 0；09 在 8 步内完成（round3 是 11 步失败）。
