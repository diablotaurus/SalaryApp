import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _loaded_modules_after_import(module: str, candidates: list[str]) -> list[str]:
    code = (
        f"import sys, {module}; "
        f"print(','.join(m for m in {candidates!r} if m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    loaded = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    return [name for name in loaded.split(",") if name]


@pytest.mark.parametrize(
    ("entry_module", "heavy_modules"),
    [
        # matplotlib (~1 с) — только при первом открытии «Аналитики»
        ("desktop.app", ["matplotlib", "pandas", "openpyxl"]),
        # openpyxl (~0.7 с) — только в момент экспорта в Excel; pandas не используется
        ("bot.main", ["pandas", "openpyxl"]),
        ("web.bootstrap", ["pandas", "openpyxl", "matplotlib"]),
    ],
)
def test_entry_points_do_not_load_heavy_libraries(entry_module, heavy_modules):
    assert _loaded_modules_after_import(entry_module, heavy_modules) == []
