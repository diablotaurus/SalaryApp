import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_desktop_app_import_does_not_load_matplotlib():
    # matplotlib грузится ~1 с — только при первом открытии «Аналитики», не при запуске.
    code = "import sys, desktop.app; print('matplotlib' in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "False"
