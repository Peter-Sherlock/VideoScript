# 运行结果独立核对报告

使用当前代码重算时长和重跑规则。表中的状态是存档在运行时的原始状态，核对列显示当前规则的结论。

| 用例 | 状态 | 轮数/工具调用 | 预计/目标(s) | 修订轨迹 | 引用素材 | 核对 |
|---|---|---|---|---|---|---|
| deepseek/01_normal | completed | 4/4 | 27.2 / 30.0 | v1:27.2s/ok | M01, M04, M05, M06 | ❌ 独立重跑规则检查未通过：shot 4 UNSUPPORTED_FACT_CONDITIONS、shot 4 UNSUPPORTED_QUANTIFIED_CLAIM、shot 6 UNSUPPORTED_FACT_CONDITIONS、shot 6 UNSUPPORTED_QUANTIFIED_CLAIM |
| deepseek/02_reference_p01 | completed | 8/10 | 27.8 / 30.0 | v1:24.6s/ok → v2:29.9s/ok → v3:27.8s/ok | B01, P01 | ✅ 一致 |
| deepseek/02b_reference_user_draft | completed | 7/8 | 25.9 / 30.0 | v1:38.9s/over → v2:23.2s/under → v3:25.6s/ok → v4:25.9s/ok | P01 | ✅ 一致 |
| deepseek/02b_reference_user_draft_rerun | completed | 8/9 | 25.4 / 30.0 | v1:38.9s/over → v2:21.5s/under → v3:23.1s/under → v4:23.1s/under → v5:25.4s/ok | P01 | ✅ 一致 |
| deepseek/03_missing_info | needs_input | 1/2 | - / - | - | - | ✅ 一致 |
| deepseek/03b_missing_info_answered | completed | 7/8 | 19.5 / 20.0 | v1:23.0s/over → v2:21.0s/over → v3:19.5s/ok | M01, M02, M03, M05, M06 | ❌ 独立重跑规则检查未通过：shot 4 UNSUPPORTED_FACT_CONDITIONS、shot 4 UNSUPPORTED_FACT_CONDITIONS、shot 4 UNSUPPORTED_QUANTIFIED_CLAIM、shot 5 UNSUPPORTED_FACT_CONDITIONS、shot 5 UNSUPPORTED_QUANTIFIED_CLAIM |
| deepseek/04_no_material | needs_input | 3/4 | - / 20.0 | - | - | ✅ 一致 |
| deepseek/05_query_rewrite | completed | 6/6 | 19.5 / 20.0 | v1:26.6s/over → v2:19.5s/ok | M01, M04, M05, M06 | ❌ 独立重跑规则检查未通过：shot 3 UNSUPPORTED_FACT_CONDITIONS、shot 3 UNSUPPORTED_QUANTIFIED_CLAIM、shot 5 UNSUPPORTED_FACT_CONDITIONS |
| deepseek/06_tool_failure_transient | completed | 9/9 | 27.8 / 30.0 | v1:39.0s/over → v2:30.9s/over → v3:28.7s/ok → v4:27.8s/ok | M01, M02, M03, M04, M05, M06 | ❌ 独立重跑规则检查未通过：shot 3 UNSUPPORTED_FACT_CONDITIONS、shot 3 UNSUPPORTED_QUANTIFIED_CLAIM、shot 5 UNSUPPORTED_FACT_CONDITIONS、shot 5 UNSUPPORTED_FACT_CONDITIONS、shot 6 UNSUPPORTED_FACT_CONDITIONS |
| deepseek/07_tool_failure_permanent | failed | 6/6 | - / 20.0 | v1:未估算 | B01, P01 | ✅ 一致 |
| deepseek/08_overtime_infeasible | failed | 8/8 | 3.5 / 3.0 | v1:7.8s/over → v2:5.4s/over → v3:2.8s/ok → v4:3.5s/over → v5:3.5s/over | M01, M02, M03, M05, M06 | ✅ 一致 |
| deepseek/09_rule_violation | completed | 8/8 | 23.3 / 25.0 | v1:31.3s/over → v2:25.1s/over → v3:22.8s/ok → v4:23.3s/ok | M01, M02, M03, M04, M05, M06 | ❌ 独立重跑规则检查未通过：shot 4 UNSUPPORTED_QUANTIFIED_CLAIM、shot 5 UNSUPPORTED_FACT_CONDITIONS、shot 5 UNSUPPORTED_FACT_CONDITIONS、shot 6 UNSUPPORTED_FACT_CONDITIONS、shot 6 UNSUPPORTED_QUANTIFIED_CLAIM |
| deepseek/10_step_limit | incomplete | 3/4 | 32.5 / 30.0 | v1:41.4s/over → v2:32.5s/over | M01, M02, M03, M04, M05, M06 | ✅ 一致 |
| mock/01_normal | completed | 7/7 | 25.1 / 30.0 | v1:40.8s/over → v2:25.1s/ok → v3:25.1s/ok | M01, M02 | ❌ 独立重跑规则检查未通过：shot 4 UNSUPPORTED_FACT_CONDITIONS、shot 4 UNSUPPORTED_QUANTIFIED_CLAIM |
| mock/02_reference_p01 | completed | 5/5 | 25.1 / 30.0 | v1:36.7s/over → v2:25.1s/ok | P01 | ✅ 一致 |
| mock/02b_reference_user_draft | completed | 8/8 | 24.7 / 30.0 | v1:38.9s/over → v2:27.9s/ok → v3:23.3s/under → v4:24.7s/ok | P01 | ✅ 一致 |
| mock/03_missing_info | needs_input | 1/1 | - / - | - | - | ✅ 一致 |
| mock/03b_missing_info_answered | completed | 8/8 | 18.5 / 20.0 | v1:32.3s/over → v2:21.5s/over → v3:18.5s/ok | M01 | ✅ 一致 |
| mock/04_no_material | needs_input | 3/3 | - / 20.0 | - | - | ✅ 一致 |
| mock/05_query_rewrite | completed | 7/7 | 19.4 / 20.0 | v1:34.1s/over → v2:22.6s/over → v3:19.4s/ok | M01 | ✅ 一致 |
| mock/06_tool_failure_transient | completed | 8/8 | 25.1 / 30.0 | v1:40.8s/over → v2:25.1s/ok → v3:25.1s/ok | M01, M02 | ❌ 独立重跑规则检查未通过：shot 4 UNSUPPORTED_FACT_CONDITIONS、shot 4 UNSUPPORTED_QUANTIFIED_CLAIM |
| mock/07_tool_failure_permanent | failed | 4/4 | - / 20.0 | v1:未估算 | P01 | ✅ 一致 |
| mock/08_overtime_infeasible | failed | 6/6 | 30.7 / 3.0 | v1:73.0s/over → v2:45.3s/over → v3:34.0s/over → v4:30.7s/over | M01, M02, M03, M05, M06 | ✅ 一致 |
| mock/09_rule_violation | completed | 9/9 | 20.7 / 25.0 | v1:30.2s/over → v2:19.4s/under → v3:20.8s/ok → v4:19.9s/under → v5:20.7s/ok | M01 | ✅ 一致 |
| mock/10_step_limit | incomplete | 3/3 | 25.1 / 30.0 | v1:40.8s/over → v2:25.1s/ok | M01, M02 | ✅ 一致 |
| review-2026-11-11/03b_missing_info_answered | completed | 6/7 | 18.5 / 20.0 | v1:23.5s/over → v2:18.5s/ok | M01, M04, M05, M06 | ❌ 独立重跑规则检查未通过：shot 3 UNSUPPORTED_QUANTIFIED_CLAIM、shot 5 UNSUPPORTED_FACT_CONDITIONS、shot 5 UNSUPPORTED_QUANTIFIED_CLAIM |
| review-2026-11-11/battery_life_draft | completed | 9/10 | 17.3 / 20.0 | v1:未估算 → v2:20.1s/over → v3:15.7s/under → v4:17.3s/ok → v5:17.3s/ok | M02 | ✅ 一致 |

## 已完成脚本：素材 ID × 分镜 × 时长 逐一对应

### deepseek/01_normal（v1）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 3.5 | - | 拍vlog最崩的不是画面，是声音。 |
| 2 | 3.2 | - | 空调风扇一开，人声全糊了。 |
| 3 | 5.8 | M01 | 试试帧跃M2，一键开AI降噪，空调风扇底噪压下去。 |
| 4 | 5.9 | M04 | 内部测试里，人声清晰度评分从3.1升到4.3。 |
| 5 | 4.4 | M05 | Type-C、Lightning都有，插上就录，不用装App。 |
| 6 | 4.4 | M06 | 首发399，想拍好vlog的先把它收了。 |

合计 27.2s，区间 [24.0, 30.0]；时长检查版本 v1、规则检查版本 v1，规则提示 无

### deepseek/02_reference_p01（v3）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 5.0 | - | 给口播视频加字幕，你还在一个字一个字敲？ |
| 2 | 3.6 | P01 | 试试帧跃剪辑 App 的字幕功能。 |
| 3 | 5.3 | P01 | 它能识别视频里的普通话语音，自动生成字幕。 |
| 4 | 5.2 | P01 | 生成之后，还能逐句手动改，念错的字自己修。 |
| 5 | 5.3 | P01 | 新手第一次剪口播，也能先把字幕这一步跑完。 |
| 6 | 3.4 | B01 | 帧跃，让每一帧都好好表达。 |

合计 27.8s，区间 [24.0, 30.0]；时长检查版本 v3、规则检查版本 v3，规则提示 ['FEATURE_MENTION_NO_SOURCE']

### deepseek/02b_reference_user_draft（v4）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 4.8 | P01 | 做口播视频，加字幕还在一个字一个字敲？ |
| 2 | 8.8 | P01 | 试试帧跃剪辑 App，它支持字幕功能，能识别视频里的普通话语音，自动生成字幕。 |
| 3 | 4.6 | P01 | 生成后识别错的地方，还能逐句手动改。 |
| 4 | 4.6 | P01 | 字幕自动生成后，逐句检查一遍就能用。 |
| 5 | 3.1 | - | 去试试吧，记得点赞关注！ |

合计 25.9s，区间 [24.0, 30.0]；时长检查版本 v4、规则检查版本 v4，规则提示 无

### deepseek/02b_reference_user_draft_rerun（v5）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 6.9 | - | 做口播视频，加字幕是不是一个字一个字地敲，眼睛都看花了？ |
| 2 | 8.8 | P01 | 试试帧跃剪辑 App，它支持字幕功能，能识别视频里的普通话语音，自动生成字幕。 |
| 3 | 5.0 | P01 | 生成后哪句识别错了，还能一句一句手动改。 |
| 4 | 4.7 | - | 新手也能上手，去试试吧，记得点赞关注！ |

合计 25.4s，区间 [24.0, 30.0]；时长检查版本 v5、规则检查版本 v5，规则提示 ['FEATURE_MENTION_NO_SOURCE']

### deepseek/03b_missing_info_answered（v3）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 3.9 | - | 下班想拍口播，声音却像在菜市场？ |
| 2 | 4.8 | M01 | 帧跃 M2 一键 AI 降噪，压住空调风扇底噪。 |
| 3 | 3.3 | M05 | 插上手机就能录，不用装 App。 |
| 4 | 3.9 | M02, M03 | 续航约 8 小时，空旷能传 50 米。 |
| 5 | 3.6 | M06 | 首发 399，口播党可以看看。 |

合计 19.5s，区间 [16.0, 20.0]；时长检查版本 v3、规则检查版本 v3，规则提示 无

### deepseek/05_query_rewrite（v2）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 4.1 | - | 上班族做口播，最怕空调风扇底噪。 |
| 2 | 3.8 | M01 | 帧跃 M2 领夹麦，一键 AI 降噪。 |
| 3 | 5.3 | M04 | 内部测试，清晰度评分 3.1 升到 4.3。 |
| 4 | 4.0 | M05 | 接收器插上手机就用，不用装 App。 |
| 5 | 2.3 | M06 | 首发 399 元。 |

合计 19.5s，区间 [16.0, 20.0]；时长检查版本 v2、规则检查版本 v2，规则提示 无

### deepseek/06_tool_failure_transient（v4）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 4.3 | - | 新手拍 vlog，最崩溃的不是画面，是声音。 |
| 2 | 5.2 | M01 | 空调风扇的底噪，帧跃 M2 一键 AI 降噪就能压。 |
| 3 | 5.2 | M04 | 内部测试，人声清晰度从 3.1 提到 4.3。 |
| 4 | 3.8 | M05 | Type-C 和 Lightning 两个版本，插上就用。 |
| 5 | 5.2 | M02, M03 | 发射器续航约 8 小时，空旷环境传输约 50 米。 |
| 6 | 4.1 | M06 | 首发价 399 元，新手入门够用了。 |

合计 27.8s，区间 [24.0, 30.0]；时长检查版本 v4、规则检查版本 v4，规则提示 无

### deepseek/09_rule_violation（v4）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 3.9 | - | 咖啡馆录口播，收音也能这么清楚？ |
| 2 | 3.3 | M05 | 帧跃 M2，插上手机就能用。 |
| 3 | 3.8 | M01 | 一键开 AI 降噪，底噪直接压下去。 |
| 4 | 4.8 | M04 | 内部测试，清晰度从 3.1 提到 4.3。 |
| 5 | 3.9 | M02, M03 | 续航约 8 小时，空旷能传 50 米。 |
| 6 | 3.6 | M06 | 首发 399，探店博主可以冲。 |

合计 23.3s，区间 [20.0, 25.0]；时长检查版本 v4、规则检查版本 v4，规则提示 无

### mock/01_normal（v3）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 4.5 | - | 拍视频的你，是不是也常被这些细节卡住？ |
| 2 | 6.7 | M01 | 帧跃 M2 支持一键开启 AI 降噪，可抑制空调、风扇等环境底噪。 |
| 3 | 4.0 | M01 | （无旁白） |
| 4 | 3.6 | M02 | 帧跃 M2 发射器续航约 8 小时。 |
| 5 | 6.3 | - | 帧跃 M2 无线麦克风，去试试吧，评论区聊聊你的拍摄需求。 |

合计 25.1s，区间 [24.0, 30.0]；时长检查版本 v3、规则检查版本 v3，规则提示 无

### mock/02_reference_p01（v2）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 4.8 | - | 拍视频的你，是不是也常被这些细节卡住？ |
| 2 | 10.5 | P01 | 帧跃剪辑 App 支持字幕功能：可识别视频中的普通话语音并自动生成字幕，生成后可逐句手动修改。 |
| 3 | 4.0 | P01 | （无旁白） |
| 4 | 5.8 | - | 帧跃剪辑 App，去试试吧，评论区聊聊你的拍摄需求。 |

合计 25.1s，区间 [24.0, 30.0]；时长检查版本 v2、规则检查版本 v2，规则提示 无

### mock/02b_reference_user_draft（v4）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 9.4 | - | 做口播视频的朋友，是不是每次加字幕都要花很久，一个字一个字地敲，眼睛都看花了？ |
| 2 | 4.3 | P01 | 今天给大家推荐帧跃剪辑 App。 |
| 3 | 4.4 | P01 | 生成以后如果有识别错的地方。 |
| 4 | 3.0 | - | 来看看它能帮你做什么。 |
| 5 | 3.6 | - | 赶紧去试试吧，记得点赞关注！ |

合计 24.7s，区间 [24.0, 30.0]；时长检查版本 v4、规则检查版本 v4，规则提示 ['FEATURE_MENTION_NO_SOURCE']

### mock/03b_missing_info_answered（v3）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 4.5 | - | 拍视频的你，是不是也常被这些细节卡住？ |
| 2 | 3.7 | M01 | 帧跃 M2 支持一键开启 AI 降噪。 |
| 3 | 4.0 | M01 | （无旁白） |
| 4 | 6.3 | - | 帧跃 M2 无线麦克风，去试试吧，评论区聊聊你的拍摄需求。 |

合计 18.5s，区间 [16.0, 20.0]；时长检查版本 v3、规则检查版本 v3，规则提示 无

### mock/05_query_rewrite（v3）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 4.8 | - | 拍视频的你，是不是也常被这些细节卡住？ |
| 2 | 3.9 | M01 | 帧跃 M2 支持一键开启 AI 降噪。 |
| 3 | 4.0 | M01 | （无旁白） |
| 4 | 6.7 | - | 帧跃 M2 无线麦克风，去试试吧，评论区聊聊你的拍摄需求。 |

合计 19.4s，区间 [16.0, 20.0]；时长检查版本 v3、规则检查版本 v3，规则提示 无

### mock/06_tool_failure_transient（v3）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 4.5 | - | 拍视频的你，是不是也常被这些细节卡住？ |
| 2 | 6.7 | M01 | 帧跃 M2 支持一键开启 AI 降噪，可抑制空调、风扇等环境底噪。 |
| 3 | 4.0 | M01 | （无旁白） |
| 4 | 3.6 | M02 | 帧跃 M2 发射器续航约 8 小时。 |
| 5 | 6.3 | - | 帧跃 M2 无线麦克风，去试试吧，评论区聊聊你的拍摄需求。 |

合计 25.1s，区间 [24.0, 30.0]；时长检查版本 v3、规则检查版本 v3，规则提示 无

### mock/09_rule_violation（v5）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 1.5 | - | 收音神器！ |
| 2 | 7.8 | M01 | 帧跃 M2 支持一键开启 AI 降噪，可抑制空调、风扇等环境底噪。 |
| 3 | 5.1 | M01 | （无旁白） |
| 4 | 6.3 | - | 帧跃 M2 无线麦克风，去试试吧，评论区聊聊你的拍摄需求。 |

合计 20.7s，区间 [20.0, 25.0]；时长检查版本 v5、规则检查版本 v5，规则提示 无

### review-2026-11-11/03b_missing_info_answered（v2）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 3.6 | - | 下班想拍口播，一录全是空调声？ |
| 2 | 3.9 | M01 | 帧跃 M2 一键 AI 降噪，压住底噪。 |
| 3 | 4.8 | M04 | 内部测试人声清晰度 3.1 升到 4.3。 |
| 4 | 3.1 | M05 | 插上手机就用，不用装 App。 |
| 5 | 3.1 | M06 | 首发 399，帧跃 M2。 |

合计 18.5s，区间 [16.0, 20.0]；时长检查版本 v2、规则检查版本 v2，规则提示 无

### review-2026-11-11/battery_life_draft（v5）

| 镜号 | 时长(s) | 素材 ID | 旁白 |
|---|---|---|---|
| 1 | 3.4 | - | 口播录到一半没电，最崩溃。 |
| 2 | 4.0 | M02 | 帧跃 M2 发射器，续航约 8 小时。 |
| 3 | 6.2 | M02 | 这个数有条件：单次充满，连续录音，实验室，关闭降噪。 |
| 4 | 3.7 | M02 | 出门拍摄心里有底，帧跃 M2。 |

合计 17.3s，区间 [16.0, 20.0]；时长检查版本 v5、规则检查版本 v5，规则提示 无
