"""运行配置：路径、执行上限、模型参数（全部可由环境变量 / .env 覆盖）。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MATERIALS_PATH = DATA_DIR / "materials.json"
RULES_PATH = DATA_DIR / "brand_rules.json"


def load_env() -> None:
    """读取项目根目录的 .env（不覆盖已存在的系统环境变量）。"""
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv 未安装时只用系统环境变量
        return
    load_dotenv(ROOT / ".env", override=False)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw and raw.strip() else default


@dataclass
class Limits:
    """执行上限：达到任一上限时返回明确的 incomplete 状态。"""

    max_steps: int = 14          # 模型决策轮数上限（每轮 = 一次模型调用）
    max_tool_calls: int = 24     # 全部工具调用次数上限
    max_calls_per_tool: int = 8  # 单个工具调用次数上限（防止对同一工具死循环）

    @classmethod
    def from_env(cls) -> "Limits":
        return cls(
            max_steps=_int_env("AGENT_MAX_STEPS", cls.max_steps),
            max_tool_calls=_int_env("AGENT_MAX_TOOL_CALLS", cls.max_tool_calls),
            max_calls_per_tool=_int_env("AGENT_MAX_CALLS_PER_TOOL", cls.max_calls_per_tool),
        )


@dataclass
class LLMSettings:
    provider: str            # deepseek | openai_compat | mock
    base_url: str
    api_key: str | None
    model: str
    thinking: str            # disabled | enabled（仅 DeepSeek 使用）
    temperature: float
    timeout_sec: float

    @classmethod
    def from_env(cls, provider: str | None = None) -> "LLMSettings":
        provider = (provider or os.getenv("LLM_PROVIDER") or "deepseek").strip().lower()
        return cls(
            provider=provider,
            base_url=os.getenv("LLM_BASE_URL") or "https://api.deepseek.com",
            api_key=os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY"),
            model=os.getenv("LLM_MODEL") or "deepseek-flash",
            thinking=(os.getenv("LLM_THINKING") or "disabled").strip().lower(),
            temperature=_float_env("LLM_TEMPERATURE", 0.3),
            timeout_sec=_float_env("LLM_TIMEOUT_SEC", 90.0),
        )
