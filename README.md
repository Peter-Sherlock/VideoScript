# 短视频脚本 Agent（题号 4）

帮助创作者生成**有事实依据、满足时长限制、可编辑**的短视频脚本。模型（DeepSeek）负责写稿和决定下一步；素材检索、时长估算、规则检查由确定性工具完成；代码护栏保证“没通过检查的版本不能交付”。

- 运行方式：**CLI**（Python）
- 模型：DeepSeek `deepseek-flash`（OpenAI 兼容接口）；无 Key 时可用离线 Mock 入口 `--llm mock`（只验证流程）
- 框架：未使用 Agent 框架，原生实现 ReAct 循环（取舍见 [docs/02-solution.md](docs/02-solution.md)）
- 数据：虚构品牌“帧跃”的合成素材与规则（[data/](data/)），不含真实公司、密钥或隐私数据

## 评审入口

| 想看什么 | 去哪里 |
|---|---|
| 需求、范围、成功标准 | [docs/01-requirements.md](docs/01-requirements.md) |
| 调用流程、动态决策、护栏、技术取舍 | [docs/02-solution.md](docs/02-solution.md) |
| 测试预期 vs 实际结果、失败与限制 | [docs/03-evaluation.md](docs/03-evaluation.md) |
| AI 辅助的范围、个人修改与验证 | [docs/04-ai-usage.md](docs/04-ai-usage.md) |
| 最难的问题、收获、下一步 | [docs/05-retrospective.md](docs/05-retrospective.md) |
| 真实模型运行记录（输入 / 输出 / trace） | [examples/deepseek/](examples/deepseek/) |
| 离线 Mock 运行记录 | [examples/mock/](examples/mock/) |
| 改进前的真实运行记录（4 轮迭代对比） | [examples/deepseek-history/](examples/deepseek-history/) |
| 独立核对报告（素材 ID × 分镜时长 × 检查结果） | [examples/verification_report.md](examples/verification_report.md) |
| 测试结果 | [examples/test_results.txt](examples/test_results.txt) |
| Agent 循环 / 工具 / 闸门代码 | [src/vsagent/agent.py](src/vsagent/agent.py)、[src/vsagent/tools/](src/vsagent/tools/) |

## 环境与安装

- Python ≥ 3.10（开发与验证使用 Python 3.14，Windows 10）
- 依赖：`openai`、`python-dotenv`、`pytest`

```bash
python -m pip install -r requirements.txt
```

配置（仅真实模型需要；Mock 模式无需任何配置）：

```bash
cp .env.example .env
```

然后在 `.env` 中填写 `DEEPSEEK_API_KEY`。全部变量及说明见 [.env.example](.env.example)。Windows PowerShell 可用 `Copy-Item .env.example .env`。

## 运行

离线 Mock（无需 Key，验证流程）：

```bash
python main.py run --input examples/inputs/02b_reference_user_draft.json --llm mock
```

真实模型（DeepSeek）运行单个用例，并把输出与运行记录写入目录：

```bash
python main.py run --input examples/inputs/02b_reference_user_draft.json --llm deepseek --out examples/runs/demo
```

故障注入（工具失败场景）：

```bash
python main.py run --input examples/inputs/01_normal.json --llm deepseek --fault search_materials:transient
```

缺信息时预置用户回答（或用 `--interactive` 在终端回答）：

```bash
python main.py run --input examples/inputs/03_missing_info.json --llm deepseek --answer "发抖音，20 秒左右"
```

批量运行全部用例：

```bash
python main.py batch --llm deepseek --out examples/deepseek
```

测试与独立核对：

```bash
python -m pytest -q
```

```bash
python scripts/verify_examples.py
```

可选：真实模型冒烟测试（会调用 API）：在 `.env` 配好 Key 后设置环境变量 `RUN_LIVE=1` 再运行 pytest。

### 常用参数

| 参数 | 说明 |
|---|---|
| `--llm deepseek\|openai_compat\|mock` | 模型提供方，默认读 `LLM_PROVIDER` |
| `--fault 工具名:transient[:n]` / `工具名:permanent` | 前 n 次失败 / 一直失败（可重复传） |
| `--answer "..."` / `--interactive` | 对 `request_user_input` 的预置回答 / 终端交互 |
| `--max-steps N` / `--max-tool-calls N` | 执行上限，达到后返回 `incomplete` |

## 输入与输出

输入用例（[examples/inputs/](examples/inputs/)）：

```json
{
  "case_id": "01_normal",
  "brief": {
    "topic": "vlog 新手收音避坑：帧跃 M2 无线麦克风", "product": "帧跃 M2 无线麦克风",
    "audience": "刚开始拍 vlog 的新手创作者", "platform": "抖音", "target_duration_sec": 30,
    "style": "轻松种草、口语化", "must_include": ["降噪"]
  },
  "run_options": {"faults": [], "answers": []}
}
```

每次运行输出（`--out` 目录下）：

| 文件 | 内容 |
|---|---|
| `output.md` | 可编辑的脚本：标题、分镜表（画面/旁白/字幕/角标/逐镜时长/素材 ID）、素材来源、检查结果、修订记录、风险、任务状态 |
| `output.json` | 同上的结构化版本，另含检索记录、初始/最终简报、运行统计 |
| `trace.md` / `trace.jsonl` | 每一步：动作、工具参数摘要、返回摘要、模型给出的决策依据、后续动作 |

任务状态：`completed`（同一版本通过时长与规则检查）/ `needs_input`（缺信息或缺素材，已提问）/ `failed`（明确无法满足，附原因与建议）/ `incomplete`（达到执行上限）。

## 验收点与用例对照

全部用例都用 DeepSeek 真实运行过，结果与预期一致（详见 [docs/03-evaluation.md](docs/03-evaluation.md)）。Mock 结果在 `examples/mock/` 下同名目录。

| 题目验收点 | 用例（点击看真实运行 trace） | 实际结果 |
|---|---|---|
| 正常生成 | [01_normal](examples/deepseek/01_normal/trace.md) | completed，27.2s / 30s，引用 M01、M04、M05、M06 |
| 参考实例：仅 P01、30 秒、不得写“效率提升80%” | [02_reference_p01](examples/deepseek/02_reference_p01/trace.md)、[02b_reference_user_draft](examples/deepseek/02b_reference_user_draft/trace.md) | 02b：用户草稿 38.9s → 压缩重估 → 25.9s，只引用 P01，删除“效率提升80%”并写入风险 |
| 缺关键信息 | [03_missing_info](examples/deepseek/03_missing_info/trace.md)、[03b_missing_info_answered](examples/deepseek/03b_missing_info_answered/trace.md) | 03：不猜平台/时长，提出 3 个问题 → needs_input；03b：用户补充后继续 → completed |
| 无素材（改写查询 / 请求补充） | [04_no_material](examples/deepseek/04_no_material/trace.md)、[05_query_rewrite](examples/deepseek/05_query_rewrite/trace.md) | 04：改写后仍无 → 请求补充素材；05：按 hint 改写产品名后命中 → completed |
| 工具失败 | [06_tool_failure_transient](examples/deepseek/06_tool_failure_transient/trace.md)、[07_tool_failure_permanent](examples/deepseek/07_tool_failure_permanent/trace.md) | 06：超时后重试成功；07：持续 503 → 明确失败，不跳过检查 |
| 超时长后的修正或明确失败 | [06](examples/deepseek/06_tool_failure_transient/trace.md)、[09](examples/deepseek/09_rule_violation/trace.md)、[08_overtime_infeasible](examples/deepseek/08_overtime_infeasible/trace.md) | 06：39.0 → 30.9 → 28.7s；09：31.3 → 25.1 → 22.8s；08：3 秒放不下 7 个必含要点 → failed，附冲突说明与建议 |
| 规则检查不通过 → 修改再检查 | [09_rule_violation](examples/deepseek/09_rule_violation/trace.md) | 用户要求的“全网最强”和超长标题被拦下 → 修改 → 重估 → 重检 → completed |
| 执行上限 → 明确未完成 | [10_step_limit](examples/deepseek/10_step_limit/trace.md) | 3 轮上限 → incomplete，附未通过检查的草稿 |

迭代过程：同一批用例共跑了 4 轮真实模型，每轮发现的问题（贴边微调、重复提交同一版本、把卖点挪进字幕钻时长口径的空子、用例假设错误等）、对应改动和前后对比都在 [examples/deepseek-history/](examples/deepseek-history/) 和 [docs/03-evaluation.md](docs/03-evaluation.md) 第 4 节。

## 项目结构

```
main.py                     CLI 入口
src/vsagent/
  agent.py                  ReAct 主循环、执行上限、输出组装
  prompts.py                系统提示词
  tools/registry.py         工具 schema、会话状态、提交闸门、故障注入
  tools/materials.py        search_materials
  tools/duration.py         estimate_duration（口径写在文件头）
  tools/rules.py            check_rules
  llm/openai_compat.py      DeepSeek / OpenAI 兼容客户端
  llm/mock.py               离线 Mock 策略（只验证流程）
  verify.py                 独立核对
  render.py / trace.py      Markdown 输出与运行记录
data/                       合成素材与品牌/平台规则
tests/                      工具单测、循环护栏测试、端到端场景测试
examples/inputs/            12 个输入用例
examples/deepseek/          真实模型运行结果（最终版）
examples/deepseek-history/  改进前各轮的真实运行结果
examples/mock/              离线 Mock 运行结果
scripts/verify_examples.py  生成独立核对报告
docs/                       01–05 文档
```

## 用时与未完成部分

- 实际用时：____（请候选人如实填写，见 [docs/04-ai-usage.md](docs/04-ai-usage.md)）
- 未完成 / 未做：界面、HTTP API、会话断点续跑、基于模型的语义级事实核对、TTS 实测时长校准、多次重复运行的统计评估（详见 [docs/05-retrospective.md](docs/05-retrospective.md)）。
