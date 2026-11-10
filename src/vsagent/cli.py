"""命令行入口。

单个用例：  python main.py run --input examples/inputs/01_normal.json --llm mock
批量用例：  python main.py batch --llm mock --out examples/mock
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import sys
from pathlib import Path
from typing import Any

from .agent import ScriptAgent
from .config import MATERIALS_PATH, ROOT, RULES_PATH, Limits, LLMSettings, load_env
from .llm import LLMError, create_llm
from .render import render_markdown
from .schema import Brief
from .tools import AnswerProvider, FaultPlan, MaterialStore


def load_case(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "brief" not in data:  # 也允许直接传简报
        data = {"brief": data}
    data.setdefault("run_options", {})
    data.setdefault("case_id", Path(path).stem)
    return data


def run_case(case: dict[str, Any], llm_provider: str | None, out_dir: Path | None,
             faults: list[str] | None = None, answers: list[str] | None = None,
             interactive: bool = False, limits: Limits | None = None) -> dict[str, Any]:
    opts = case.get("run_options", {})
    settings = LLMSettings.from_env(llm_provider)
    llm = create_llm(settings)
    limits = Limits(**vars(limits)) if limits else Limits.from_env()
    for key, value in (opts.get("limits") or {}).items():  # 用例可单独收紧上限（演示 incomplete）
        setattr(limits, key, int(value))
    agent = ScriptAgent(
        llm=llm,
        store=MaterialStore(MATERIALS_PATH),
        rules=json.loads(RULES_PATH.read_text(encoding="utf-8")),
        limits=limits,
        faults=FaultPlan.parse(faults if faults is not None else opts.get("faults")),
        answers=AnswerProvider(answers if answers is not None else opts.get("answers"), interactive=interactive),
    )
    result = agent.run(Brief.from_dict(case["brief"]))
    output = {"case_id": case["case_id"], "case_description": case.get("description"), **result.output}
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "input.json").write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "output.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "output.md").write_text(render_markdown(output), encoding="utf-8")
        result.trace.write_jsonl(out_dir / "trace.jsonl")
        (out_dir / "trace.md").write_text(
            result.trace.to_markdown(f"运行记录：{case['case_id']}（{output['run']['llm']}）"), encoding="utf-8")
    return output


def _print_summary(output: dict[str, Any]) -> None:
    print(f"[{output['case_id']}] status={output['status']} | {output['status_reason']}")
    if output.get("estimated_total_sec") is not None:
        print(f"    预计总时长 {output['estimated_total_sec']}s / 目标 {output.get('target_duration_sec')}s，"
              f"版本 {output.get('script_version')}，修订 {[v['version'] for v in output['revision_history']]}")
    if output.get("questions"):
        print(f"    待补充：{output['questions']}")
    print(f"    决策轮数 {output['run']['steps_used']}，工具调用 {output['run']['tool_calls_used']} 次")


def main(argv: list[str] | None = None) -> int:
    load_env()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="vsagent", description="短视频脚本 Agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="运行单个用例")
    p_run.add_argument("--input", required=True, help="用例 JSON（含 brief 与可选 run_options）")
    p_run.add_argument("--out", help="输出目录（写入 output.json/output.md/trace.jsonl/trace.md）")
    p_run.add_argument("--fault", action="append", help="故障注入，如 search_materials:transient 或 estimate_duration:permanent")
    p_run.add_argument("--answer", action="append", help="预置用户对补充请求的回答（可多次）")
    p_run.add_argument("--interactive", action="store_true", help="补充请求时在终端提问")

    p_batch = sub.add_parser("batch", help="批量运行 examples/inputs 下全部用例")
    p_batch.add_argument("--inputs", default=str(ROOT / "examples" / "inputs"))
    p_batch.add_argument("--out", required=True)
    p_batch.add_argument("--only", nargs="*", help="只运行指定 case_id 前缀")
    p_batch.add_argument("--workers", type=int, default=1, help="并发运行的用例数（默认 1）")

    for p in (p_run, p_batch):
        p.add_argument("--llm", choices=["deepseek", "openai_compat", "mock"], help="默认读 LLM_PROVIDER，缺省 deepseek")
        p.add_argument("--max-steps", type=int)
        p.add_argument("--max-tool-calls", type=int)

    args = parser.parse_args(argv)
    limits = Limits.from_env()
    if args.max_steps:
        limits.max_steps = args.max_steps
    if args.max_tool_calls:
        limits.max_tool_calls = args.max_tool_calls

    try:
        if args.cmd == "run":
            case = load_case(Path(args.input))
            output = run_case(case, args.llm, Path(args.out) if args.out else None, faults=args.fault,
                              answers=args.answer, interactive=args.interactive, limits=limits)
            _print_summary(output)
            if not args.out:
                print(render_markdown(output))
        else:
            files = sorted(Path(args.inputs).glob("*.json"))
            if args.only:
                files = [f for f in files if any(f.stem.startswith(p) for p in args.only)]
            cases = [load_case(f) for f in files]
            with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:  # 用例之间互不共享状态
                futures = [pool.submit(run_case, c, args.llm, Path(args.out) / c["case_id"], limits=limits)
                           for c in cases]
                for fut in futures:
                    _print_summary(fut.result())
    except LLMError as exc:
        print(f"模型不可用：{exc}\n可改用离线模式：--llm mock", file=sys.stderr)
        return 2
    return 0
