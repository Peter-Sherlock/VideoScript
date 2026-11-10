# 03 评估：测试预期、实际结果、失败与限制

## 1. 评估方法

| 层次 | 证明什么 | 怎么跑 | 结果文件 |
|---|---|---|---|
| 单元 + 循环护栏测试 | 工具计算正确；闸门、上限、故障、重复提交等护栏有效（用预设工具调用序列的假模型驱动，与模型能力无关） | `python -m pytest -q` | [examples/test_results.txt](../examples/test_results.txt) |
| 离线 Mock 端到端 | 无 Key 时整条流程可跑通、输出结构正确 | `python main.py batch --llm mock --out examples/mock` | [examples/mock/](../examples/mock/) |
| **真实模型运行（DeepSeek）** | 模型能否根据不同工具结果调整动作 | `python main.py batch --llm deepseek --out examples/deepseek` | [examples/deepseek/](../examples/deepseek/) |
| 独立核对 | 不信任 output.json 的结论，用工具代码重算逐镜时长、重跑规则、核对素材 ID | `python scripts/verify_examples.py` | [examples/verification_report.md](../examples/verification_report.md) |
| 迭代对比 | 每次改动前后同输入重跑，看改动是否有效 | 见第 4 节 | [examples/deepseek-history/](../examples/deepseek-history/) |

运行环境：Windows 10，Python 3.14.7；模型 `deepseek-flash`（`thinking: disabled`，`temperature=0.3`）；上限：14 轮决策 / 24 次工具调用 / 单工具 8 次。时长通过区间为 [0.8×目标, 目标]。

## 2. 测试预期 vs 实际结果（最终版，DeepSeek 真实运行）

每个用例只跑一次（02b 跑两次，用来观察同输入下的差异）。点击用例名可打开对应 trace。

| 用例 | 验收点 | 预期 | 实际状态 | 轮数/工具调用 | 各版本预计时长与规则结果 | 引用素材 |
|---|---|---|---|---|---|---|
| [01_normal](../examples/deepseek/01_normal/trace.md) | 正常生成 | completed | ✅ completed | 4/4 | 27.2s 规则通过 | M01,M04,M05,M06 |
| [02_reference_p01](../examples/deepseek/02_reference_p01/trace.md) | 参考实例：仅 P01；用户要“效率提升80%” | completed，不出现效果数据 | ✅ completed | 8/10 | 24.6s → 29.9s 违规:UNSUPPORTED_FEATURE → 27.8s 规则通过 | B01,P01 |
| [02b_reference_user_draft](../examples/deepseek/02b_reference_user_draft/trace.md) | 参考实例压缩路径：用户草稿约 38s、含“效率提升80%” | 先超时 → 压缩重估 → 删除无依据结论 | ✅ completed | 7/8 | **38.9s** → 23.2s → 25.6s 违规:MISSING_SOURCE → 25.9s 规则通过 | P01 |
| [02b_reference_user_draft_rerun](../examples/deepseek/02b_reference_user_draft_rerun/trace.md) | 同上（第二次运行） | 同上 | ✅ completed | 8/9 | **38.9s** → 21.5s → 23.1s → 23.1s → 25.4s 规则通过 | P01 |
| [03_missing_info](../examples/deepseek/03_missing_info/trace.md) | 缺关键信息 | needs_input，不猜平台/时长 | ✅ needs_input | 1/2 | - | - |
| [03b_missing_info_answered](../examples/deepseek/03b_missing_info_answered/trace.md) | 缺信息 → 用户补充后继续 | completed | ✅ completed | 7/8 | 23.0s → 21.0s → 19.5s 规则通过 | M01,M02,M03,M05,M06 |
| [04_no_material](../examples/deepseek/04_no_material/trace.md) | 无素材 | 改写后仍无 → needs_input | ✅ needs_input | 3/4 | - | - |
| [05_query_rewrite](../examples/deepseek/05_query_rewrite/trace.md) | 检索无结果 → 改写查询 | 改写后命中 → completed | ✅ completed | 6/6 | 26.6s → 19.5s 规则通过 | M01,M04,M05,M06 |
| [06_tool_failure_transient](../examples/deepseek/06_tool_failure_transient/trace.md) | 工具失败（可恢复） | 重试后 completed | ✅ completed | 9/9 | 39.0s → 30.9s → 28.7s 违规:BANNED_WORD → 27.8s 规则通过 | M01–M06 |
| [07_tool_failure_permanent](../examples/deepseek/07_tool_failure_permanent/trace.md) | 工具失败（持续） | failed，不跳过检查 | ✅ failed | 6/6 | 未估算（503 ×3） | （草稿）B01,P01 |
| [08_overtime_infeasible](../examples/deepseek/08_overtime_infeasible/trace.md) | 超时长后明确失败 | failed，说明冲突与建议 | ✅ failed | 8/8 | 7.8s → 5.4s → 2.8s 违规:MISSING_REQUIRED_POINT → 3.5s → 3.5s | （草稿）M01,M02,M03,M05,M06 |
| [09_rule_violation](../examples/deepseek/09_rule_violation/trace.md) | 规则不通过 → 修改再检查 | 删除极限词后 completed | ✅ completed | 8/8 | 31.3s → 25.1s → 22.8s 违规:BANNED_WORD/TITLE_TOO_LONG → 23.3s 规则通过 | M01–M06 |
| [10_step_limit](../examples/deepseek/10_step_limit/trace.md) | 执行上限（max_steps=3） | incomplete | ✅ incomplete | 3/4 | 41.4s → 32.5s（附未通过的草稿） | M01–M06 |

**结论：13 次运行全部符合预期。** 独立核对报告中 25 个结果（DeepSeek 13 个 + Mock 12 个）全部“✅ 一致”：每个 completed 脚本的逐镜时长之和等于总时长、重算结果与输出一致、时长与规则检查绑定同一版本、所有素材 ID 都存在且在本次会话中被检索到。

成本参考：最终 13 次运行合计约 42.5 万输入 token、3.4 万输出 token，模型耗时平均约 36 秒/次（不含工具执行，工具都是本地函数）。

## 3. 关键运行记录解读

### 3.1 参考实例：P01 + 30 秒 + “效率提升80%”
**02b**（[trace](../examples/deepseek/02b_reference_user_draft/trace.md) / [脚本](../examples/deepseek/02b_reference_user_draft/output.md)）与题目参考实例逐项对应：

| 题目要求 | 实际记录 |
|---|---|
| 首稿估算 38 秒时应压缩并重新估算 | 第 1 步估算用户草稿 v1 = **38.9s（超时）**；第 2 步按 `cut_plan` 删约 50 字并去掉“效率提升80%” → v2 = 23.2s（过短）；补约 16 字有依据内容 → v3 = 25.6s；规则检查发现镜头缺来源 → v4 = **25.9s**，时长与规则均通过后提交 |
| 输出包含分镜、P01 引用及总时长 | 5 个分镜、逐镜时长、P01 原文与出处、总时长 25.9s（[output.md](../examples/deepseek/02b_reference_user_draft/output.md)） |
| 无效果数据时不得添加“效率提升80%”等结论 | 模型删掉了草稿中的“效率提升80%”，并在风险中写明原因；把“省下不少功夫”这类效果说法改成流程描述 |

**02**（模型从零写稿）中，用户在需求里主动要“效率提升80%”。模型先专门检索 `effect_data`，结果 0 条，于是在风险中写明“素材库无任何效果数据，因此脚本未写任何效率数字”。首稿 24.6s 刚过下限，模型主动向建议的 27s 靠拢，补了一个使用场景镜头（29.9s）。规则检查发现新镜头引用的是品牌口号 B01，却提到了“字幕”功能（UNSUPPORTED_FEATURE）；模型把这句话归到引用 P01 的镜头，改后为 27.8s，两项检查都通过。

### 3.2 同一决策点、不同工具结果 → 不同动作（题目要求的“两条执行路径”）

| 决策点 | 路径 A | 路径 B |
|---|---|---|
| 首次检索 0 条 | **05**：hint 中的“帧跃 M2 无线麦克风”与用户写的“帧越 M2 领夹麦”相近 → 改写产品名重查 → 命中 6 条 → 写稿 → completed | **04**：“帧跃 X1 智能云台”与现有产品都不相近 → 去掉产品过滤、换关键词再查 → 仍 0 条（另一次检索只命中品牌口号 B01，没有产品事实）→ `request_user_input`，询问 X1 是否已上市，请用户补充官方参数与卖点，或改做现有产品 → needs_input |
| 工具报错 | **06**：search 超时（retryable）→ 重试同一查询 → 成功 → completed | **07**：estimate 连续 3 次 503 → `report_failure`：“无法获得时长结果，按规则不能跳过时长校验提交” |
| 缺关键字段 | **03**：没有预置回答 → 提出平台、时长、受众/风格 3 个问题 → needs_input | **03b**：预置回答“发抖音，20 秒左右，面向想做口播的上班族” → `update_brief` 只写入用户说过的平台、时长、受众；风格未提及，作为假设写进风险 → 写稿 → completed |
| 时长检查结果 | **01**：首稿 27.2s 通过 → 直接做规则检查 | **06**：首稿 39.0s 超时 → 按逐镜建议压缩 → 30.9 → 28.7s |

### 3.3 超时长：修正 vs 明确失败
- **修正**：06（39.0 → 30.9 → 28.7s）、09（31.3 → 25.1 → 22.8s）、03b（23.0 → 21.0 → 19.5s）、05（26.6 → 19.5s）、02b（38.9 → 23.2 → 25.6 → 25.9s）。
- **明确失败**：08 要求 3 秒内讲全 7 个要点。模型先尝试把要点写进标题（v3 估算 2.8s），被规则拦下（标题不算“包含”）；改用字幕后为 3.5s，仍超上限。最终 `report_failure` 写明冲突（7 个要点仅字幕阅读就要约 3.25s），并给出 4 条建议，例如“放宽到 4 秒”“3 秒只保留降噪、续航、首发价 399 三个要点”。

### 3.4 执行上限
10 用例把决策轮数限制为 3，第 3 轮结束时返回 `incomplete`：“达到最大决策轮数上限 3，任务未完成”，并附上最后一个版本（32.5s，未通过）供用户继续编辑，标注“不可直接发布”。

### 3.5 Mock 与测试
- Mock 12 个用例的状态与 DeepSeek 一致（[examples/mock/](../examples/mock/)）。Mock 的决策是写死的启发式，只用于验证流程，每个 Mock 输出都带有这条说明。
- pytest：62 passed，1 skipped（真实 API 冒烟测试，需 `RUN_LIVE=1`）。覆盖三个工具（含“效率提升80%”“八成”“大幅提升”拦截、免责声明、极限词、“第一步”不误伤、字幕阅读时间、逐镜删减建议）；循环护栏（未检查/检查版本不一致时拒绝提交、步数/调用/单工具上限、故障不自动重试、`update_brief` 不能改用户已给定的字段、重复提交）；以及端到端场景。

## 4. 迭代改进：真实运行发现的问题 → 改动 → 效果

同一批用例共跑了 4 轮真实模型，每轮改动前的结果都保存在 [examples/deepseek-history/](../examples/deepseek-history/)（含每轮详细说明）。

| 轮次 | 发现的问题（证据） | 改动 |
|---|---|---|
| round1 → round2 | 只告诉模型“超出上限 X 秒”时，它每次删 1–3 字、贴着上限反复估算（01：30.6 → 30.4 → 30.2 → 30.0）；03b 因此撞上单工具上限而失败 | 估算结果增加 `recommended_sec`（区间中部）与对应删减字数 |
| | 模型声称“这次真正改了”，实际原样重复提交同一版本（03b、06、08） | 提示“与 vN 完全相同” |
| | 08 原设“10 秒讲不完 4 个要点”，真实模型写出了 10.0s 的版本 | 用例改为 5 秒 6 要点；新增 02b |
| round2 → round3 | 只给提示不够：08 中模型在提示“未修改”后仍原样提交 6 次 | 改为 `DUPLICATE_SUBMISSION` 错误，并给出“实际修改或 report_failure”两个选项 |
| | 模型把卖点挪进长字幕、口播只留关键词来压时长 | 每镜取口播与字幕阅读时间的较大值；必含要点不认角标小字 |
| | 首稿普遍偏长（30 秒目标首稿 34–38s） | 首条消息给出“约 N 字旁白”的写稿参考 |
| round3 → final | 建议“约删 17 字”，模型每次只删 2 字（09：26.2 → 25.7 → 25.5 → 25.1，失败） | 超时结果附逐镜删减建议 `cut_plan` |
| | 08 再次可解（6 要点全放字幕、口播只留品牌名，4.8s）；标题也被算作“包含要点” | 必含要点只认旁白/字幕；用例改为 3 秒 7 要点（按口径最短 3.5s） |
| | 03b 中模型把用户没提过的风格写进简报，风格会影响语速口径 | `update_brief` 只接受能在用户回答中找到依据的值 |
| | 02b 两次运行都没有先测草稿（模型先改写再估算） | 用例需求写明“先帮我测一下现在有多长”（贴近真实用户说法；怎么改仍由模型决定） |

可量化的效果（同一用例在各轮的决策轮数）：

| 用例 | round1 | round2 | round3 | final |
|---|---|---|---|---|
| 01_normal | 12 步 | 4 步 | 5 步 | 4 步 |
| 03b_missing_info_answered | 12 步 **failed** | 9 步 | 7 步 | 7 步 |
| 06_tool_failure_transient | 12 步 | 9 步 | 8 步 | 9 步 |
| 09_rule_violation | 7 步 | 10 步 | 11 步 **failed** | 8 步 |
| 全部用例中“重复估算同一版本”的次数 | 8 | 8 | 3 | **0** |

## 5. 失败与限制

1. **单次运行，存在随机性。** 每个用例只跑了 1 次（02b 2 次），结果不代表稳定的成功率。历史记录里能看到同一份代码下的不同表现：round3 中 09 失败、其它轮次成功；round4 批量中 02b 两次都没先测草稿就一次通过（见 `deepseek-history/round4/`）。要得到可信的完成率，需要每个用例重复跑 N 次并统计。
2. **模型仍有“贴边”倾向。** 即使有建议时长和逐镜删减建议，模型有时仍压到区间边缘（02b_rerun 21.5 → 23.1 → 23.1 → 25.4s，用了 8 步）。护栏能保证结果正确，但不能保证步数最少。
3. **（已修复）风格假设曾被写进简报并影响时长口径。** 第四轮的 03b 中，用户没提风格，模型通过 `update_brief` 写入了自己假设的“快节奏带货口播”；风格决定语速口径（快节奏按 5.0 字/秒，默认 4.5），等于间接放宽了时长检查（记录见 `deepseek-history/round4/03b_missing_info_answered`）。已改为：`update_brief` 写入的值必须能在用户回答里找到（数字原样出现、文本至少 60% 的字出现），否则拒绝并提示“这是你的假设，请写进 risks”。最终 03b 重跑时模型只写入了平台、时长、受众，风格作为假设写进风险；该护栏由单测 `test_update_brief_rejects_values_not_in_user_reply` 覆盖。
4. **规则检查是词表 + 数字匹配，不是语义判断。** 能拦住“效率提升80%”“八成”“大幅提升”、无依据功能词、无来源数字；拦不住同义改写的隐含效果（如“几乎不用改”）。“宣称词”启发式也可能漏判没有宣称词的产品宣称（只会降为提示）。
5. **时长估算是经验公式**（字数 ÷ 语速 + 停顿 + 转场，字幕按 6 字/秒），未用真实配音校准；不同配音员语速差异可能有 ±15%。
6. **用例设计本身也出过错。** 08 的“做不到”假设两次被真实模型推翻（10 秒 4 要点、5 秒 6 要点都能做到），最终版按工具口径计算了下限（3.5s）才确定不可行。说明“明确失败”类用例要按口径算出理论下限，不能凭直觉设。
7. **needs_input 不能断点续跑。** 用户补充后需要重新运行（或用 `--answer` / `--interactive` 在同一次运行内补充）。
8. **Mock 的局限。** Mock 的压缩策略简单（删解释句 → 缩分句 → 删卖点），结果只证明流程正确，不代表写稿质量。
9. **最终结果中 08 的新输入、02b 的需求文字和 `update_brief` 的校验是在第四轮批量之后修改的**，因此 08、02b（两次）、03b 是用最终代码和输入单独重跑的。其余用例的批量运行早于“必含要点只认旁白/字幕”这一规则改动，但独立核对器已用最终规则重新检查所有输出，全部通过（该改动只影响带 must_include 的用例，即 01 与 08）。
