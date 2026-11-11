"""命令行入口：README 中的命令可用；错误输入给出可读提示而不是异常堆栈。"""
import json

import pytest
from conftest import ScriptedLLM

from vsagent.agent import ScriptAgent
from vsagent.cli import main
from vsagent.config import ROOT, Limits
from vsagent.schema import Brief
from vsagent.tools import AnswerProvider, FaultPlan

INPUTS = ROOT / "examples" / "inputs"


def test_run_with_out_dir_writes_all_files(tmp_path):
    out = tmp_path / "demo"
    assert main(["run", "--input", str(INPUTS / "02b_reference_user_draft.json"), "--llm", "mock",
                 "--out", str(out)]) == 0
    assert {p.name for p in out.iterdir()} == {"input.json", "output.json", "output.md", "trace.jsonl", "trace.md"}


def test_answer_flag_continues_after_missing_info(tmp_path):
    assert main(["run", "--input", str(INPUTS / "03_missing_info.json"), "--llm", "mock",
                 "--answer", "发抖音，20 秒左右", "--out", str(tmp_path)]) == 0
    out = json.loads((tmp_path / "output.json").read_text(encoding="utf-8"))
    assert out["status"] == "completed" and out["brief_final"]["platform"] == "抖音"


def test_fault_flag_is_injected(tmp_path):
    assert main(["run", "--input", str(INPUTS / "01_normal.json"), "--llm", "mock",
                 "--fault", "search_materials:transient", "--out", str(tmp_path)]) == 0
    assert "TIMEOUT" in (tmp_path / "trace.jsonl").read_text(encoding="utf-8")


def test_missing_input_file_is_reported(capsys):
    assert main(["run", "--input", "examples/inputs/nope.json", "--llm", "mock"]) == 2
    assert "找不到输入文件" in capsys.readouterr().err


def test_bad_fault_spec_is_reported(capsys):
    assert main(["run", "--input", str(INPUTS / "01_normal.json"), "--llm", "mock",
                 "--fault", "search_materials:sometimes"]) == 2
    assert "参数错误" in capsys.readouterr().err


def test_missing_api_key_suggests_mock(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")
    assert main(["run", "--input", str(INPUTS / "01_normal.json"), "--llm", "deepseek"]) == 2
    assert "--llm mock" in capsys.readouterr().err


def test_interactive_eof_means_no_answer(store, rules):
    """--interactive 时输入流结束（如管道输入用完）不应崩溃，按“用户未补充”处理。"""
    def eof(_prompt):
        raise EOFError

    assert AnswerProvider(interactive=True, ask=eof).get(["时长？"]) is None
    agent = ScriptAgent(ScriptedLLM([("request_user_input", {"questions": ["时长？"]})]), store, rules,
                        Limits(), FaultPlan(), AnswerProvider(interactive=True, ask=eof))
    assert agent.run(Brief.from_dict({"product": "帧跃 M2 无线麦克风"})).output["status"] == "needs_input"


def test_interactive_answer_is_used(store, rules):
    steps = [("request_user_input", {"questions": ["平台和时长？"]}),
             ("update_brief", {"platform": "小红书", "target_duration_sec": 25})]
    agent = ScriptAgent(ScriptedLLM(steps), store, rules, Limits(max_steps=2), FaultPlan(),
                        AnswerProvider(interactive=True, ask=lambda _p: "小红书，25秒"))
    final = agent.run(Brief.from_dict({"product": "帧跃 M2 无线麦克风"})).output["brief_final"]
    assert final["platform"] == "小红书" and final["target_duration_sec"] == 25.0


@pytest.mark.parametrize(("payload", "message"), [
    ("[]", "JSON 对象"),
    ('{"brief": []}', "brief"),
    ('{"target_duration_sec": "NaN"}', "正数"),
    ('{"target_duration_sec": -1}', "正数"),
    ('{"run_options": {"limits": {"max_steps": 0}}, "brief": {}}', "正整数"),
])
def test_malformed_case_is_reported_as_input_error(tmp_path, capsys, payload, message):
    path = tmp_path / "bad.json"
    path.write_text(payload, encoding="utf-8")
    assert main(["run", "--input", str(path), "--llm", "mock"]) == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize("case_id", ["../escaped", "out:stream", "CON.txt"])
def test_batch_rejects_unsafe_output_names(tmp_path, capsys, case_id):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    case = json.loads((INPUTS / "01_normal.json").read_text(encoding="utf-8"))
    (inputs / "bad.json").write_text(json.dumps({**case, "case_id": case_id}), encoding="utf-8")
    assert main(["batch", "--inputs", str(inputs), "--out", str(tmp_path / "out"), "--llm", "mock"]) == 2
    assert "case_id" in capsys.readouterr().err
    assert not (tmp_path / "out").exists() and not (tmp_path / "escaped").exists()


def test_case_limits_cannot_raise_cli_budget(tmp_path):
    case = json.loads((INPUTS / "01_normal.json").read_text(encoding="utf-8"))
    case["run_options"] = {"limits": {"max_steps": 9}}
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case), encoding="utf-8")
    out_dir = tmp_path / "out"
    assert main(["run", "--input", str(path), "--out", str(out_dir), "--llm", "mock", "--max-steps", "1"]) == 0
    out = json.loads((out_dir / "output.json").read_text(encoding="utf-8"))
    assert out["status"] == "incomplete" and out["run"]["steps_used"] == 1


def test_batch_reports_no_matching_cases(tmp_path, capsys):
    assert main(["batch", "--inputs", str(tmp_path), "--out", str(tmp_path / "out"), "--llm", "mock"]) == 2
    assert "没有匹配" in capsys.readouterr().err


def test_batch_rejects_case_insensitive_output_collisions(tmp_path, capsys):
    inputs, out = tmp_path / "inputs", tmp_path / "out"
    inputs.mkdir()
    case = json.loads((INPUTS / "01_normal.json").read_text(encoding="utf-8"))
    for idx, name in enumerate(("example", "Example")):
        (inputs / f"{idx}.json").write_text(json.dumps({**case, "case_id": name}), encoding="utf-8")
    assert main(["batch", "--inputs", str(inputs), "--out", str(out), "--llm", "mock", "--workers", "2"]) == 2
    assert "输出目录与另一用例重复" in capsys.readouterr().err
    assert not out.exists()
