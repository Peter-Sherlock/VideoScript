"""命令行入口。

单个用例：  python main.py run --input examples/inputs/01_normal.json --llm mock
批量用例：  python main.py batch --llm mock --out examples/mock
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import re
import sys
from pathlib import Path
from typing import Any

from .agent import ScriptAgent
from .config import MATERIALS_PATH, ROOT, RULES_PATH, Limits, LLMSettings, load_env
from .llm import LLMError, create_llm
from .render import render_markdown
from .schema import Brief
from .tools import AnswerProvider, FaultPlan, MaterialStore

_CASE_ID = re.compile(r"[\w-]+(?:\.[\w-]+)*")
_WINDOWS_DEVICE = re.compile(r"con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³]", re.IGNORECASE)


def load_case(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} 的输入必须是 JSON 对象")
    if "brief" not in data:  # 也允许直接传简报
        data = {"brief": data}
    data.setdefault("run_options", {})
    data.setdefault("case_id", Path(path).stem)
    try:
        Brief.from_dict(data["brief"])
        _case_options(data)
    except ValueError as exc:
        raise ValueError(f"{path.name}：{exc}") from exc
    return data


def _case_options(case: dict[str, Any]) -> dict[str, Any]:
    opts = case.get("run_options", {})
    if not isinstance(opts, dict):
        raise ValueError("run_options 必须是 JSON 对象")
    overrides = opts.get("limits", {})
    if not isinstance(overrides, dict) or overrides.keys() - vars(Limits()).keys():
        raise ValueError("run_options.limits 必须是只含已知上限字段的 JSON 对象")
    Limits(**overrides)
    for key in ("faults", "answers"):
        items = opts.get(key, [])
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            raise ValueError(f"run_options.{key} 必须是字符串数组")
    return opts


def _batch_targets(cases: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    root = out_dir.resolve()
    names, seen_paths, targets = set(), set(), []
    for case in cases:
        name = case["case_id"]
        if (not isinstance(name, str) or not _CASE_ID.fullmatch(name)
                or _WINDOWS_DEVICE.fullmatch(name.partition(".")[0])):
            raise ValueError(f"case_id 不是有效的输出目录名：{name!r}")
        target = (root / name).resolve()
        if target == root or not target.is_relative_to(root):
            raise ValueError(f"case_id {name!r} 的输出目录不在 --out 下")
        if name.casefold() in names or target in seen_paths:
            raise ValueError(f"case_id {name!r} 的输出目录与另一用例重复")
        names.add(name.casefold())
        seen_paths.add(target)
        targets.append(target)
    return targets


def run_case(case: dict[str, Any], llm_provider: str | None, out_dir: Path | None,
             faults: list[str] | None = None, answers: list[str] | None = None,
             interactive: bool = False, limits: Limits | None = None) -> dict[str, Any]:
    opts = _case_options(case)
    brief = Brief.from_dict(case["brief"])
    limits = limits if limits is not None else Limits.from_env()
    limits = replace(limits, **{key: min(value, getattr(limits, key))
                                for key, value in opts.get("limits", {}).items()})
    settings = LLMSettings.from_env(llm_provider)
    llm = create_llm(settings)
    agent = ScriptAgent(
        llm=llm,
        store=MaterialStore(MATERIALS_PATH),
        rules=json.loads(RULES_PATH.read_text(encoding="utf-8")),
        limits=limits,
        faults=FaultPlan.parse(faults if faults is not None else opts.get("faults")),
        answers=AnswerProvider(answers if answers is not None else opts.get("answers"), interactive=interactive),
    )
    result = agent.run(brief)
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
    # Windows 下管道/重定向默认按 GBK 编解码：统一用 UTF-8，避免中文乱码（含 --interactive 的管道输入）
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):  # 被测试框架替换过的流等情况，保持原样
            pass
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
    try:  # 先校验输入文件和故障参数，给出可读的错误而不是异常堆栈
        limits = replace(Limits.from_env(), **{
            key: value for key in ("max_steps", "max_tool_calls")
            if (value := getattr(args, key)) is not None
        })
        cases = ([load_case(Path(args.input))] if args.cmd == "run"
                 else [load_case(f) for f in sorted(Path(args.inputs).glob("*.json"))
                       if not args.only or any(f.stem.startswith(p) for p in args.only)])
        if args.cmd == "batch":
            if not cases:
                raise ValueError(f"没有匹配的用例：{args.inputs}")
            if args.workers < 1:
                raise ValueError("--workers 必须是正整数")
            targets = _batch_targets(cases, Path(args.out))
        for c in cases:
            FaultPlan.parse(args.fault if args.cmd == "run" and args.fault else c["run_options"].get("faults"))
    except FileNotFoundError as exc:
        print(f"找不到输入文件：{exc.filename}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"输入文件不是合法 JSON：{exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 2

    try:
        if args.cmd == "run":
            case = cases[0]
            output = run_case(case, args.llm, Path(args.out) if args.out else None, faults=args.fault,
                              answers=args.answer, interactive=args.interactive, limits=limits)
            _print_summary(output)
            if not args.out:
                print(render_markdown(output))
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:  # 用例之间互不共享状态
                futures = [pool.submit(run_case, c, args.llm, target, limits=limits)
                           for c, target in zip(cases, targets)]
                for fut in futures:
                    _print_summary(fut.result())
    except LLMError as exc:
        print(f"模型不可用：{exc}\n可改用离线模式：--llm mock", file=sys.stderr)
        return 2
    return 0
