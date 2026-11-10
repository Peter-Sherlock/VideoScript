"""项目入口：python main.py run --input examples/inputs/01_normal.json --llm mock"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from vsagent.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
