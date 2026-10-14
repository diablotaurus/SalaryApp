import re
from pathlib import Path

import pytest

import scripts.deploy_to_prod as deploy


class _FakeScheduler:
    """Подмена PowerShell: тесты не должны трогать настоящий Планировщик этого ПК."""

    def __init__(self):
        self.states: dict[str, str] = {}   # задача -> состояние; нет ключа — задачи нет
        self.restart_result = "Running"
        self.restarted: list[str] = []

    def __call__(self, script: str) -> str:
        if "Stop-ScheduledTask" in script:
            task = re.search(r"\$t = '([^']+)'", script).group(1)
            self.restarted.append(task)
            return self.restart_result
        task = re.search(r"-TaskName '([^']+)'", script).group(1)
        return self.states.get(task, "")


@pytest.fixture(autouse=True)
def scheduler(monkeypatch):
    fake = _FakeScheduler()
    monkeypatch.setattr(deploy, "_run_powershell", fake)
    return fake


def _write(path: Path, content: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_source(root: Path) -> None:
    _write(root / "version.txt", "9.9.9 current")
    _write(root / "StartSalary.pyw")
    _write(root / "run_web.py")
    _write(root / "run_bot.py")
    _write(root / "desktop" / "app.py")
    _write(root / "bot" / "main.py")
    _write(root / "core" / "config" / "settings.py")
    _write(root / "requirements.txt")


def _create_production(root: Path) -> None:
    _write(root / "prod.marker", "REAL DATA")
    _write(root / "version.txt", "1.0.0")
    _write(root / "old_code.txt", "old")
    _write(root / "bot" / ".env", "BOT_TOKEN=production")


def test_yes_mode_stops_when_backup_fails(tmp_path, monkeypatch):
    source = tmp_path / "source"
    production = tmp_path / "production"
    _create_source(source)
    _create_production(production)

    monkeypatch.setattr(deploy, "SOURCE_DIR", source)
    monkeypatch.setattr(deploy, "create_backup_before_update", lambda *_: None)
    monkeypatch.setattr(
        "sys.argv", ["deploy_to_prod.py", str(production), "--yes"]
    )

    assert deploy.main() == 1
    assert (production / "old_code.txt").read_text(encoding="utf-8") == "old"


def test_copy_failure_rolls_back_previous_production(tmp_path, monkeypatch):
    source = tmp_path / "source"
    production = tmp_path / "production"
    _create_source(source)
    _create_production(production)

    monkeypatch.setattr(deploy, "SOURCE_DIR", source)
    monkeypatch.setattr(
        deploy,
        "copy_with_exclusions",
        lambda *_args: (0, 0, ["simulated copy failure"]),
    )
    monkeypatch.setattr(
        "sys.argv", ["deploy_to_prod.py", str(production), "--yes"]
    )

    assert deploy.main() == 1
    assert (production / "old_code.txt").read_text(encoding="utf-8") == "old"
    assert (production / "bot" / ".env").read_text(encoding="utf-8") == (
        "BOT_TOKEN=production"
    )


def test_successful_deploy_preserves_marker_and_secret(tmp_path, monkeypatch):
    source = tmp_path / "source"
    production = tmp_path / "production"
    _create_source(source)
    _create_production(production)

    monkeypatch.setattr(deploy, "SOURCE_DIR", source)
    monkeypatch.setattr(
        "sys.argv", ["deploy_to_prod.py", str(production), "--yes"]
    )

    assert deploy.main() == 0
    assert not (production / "old_code.txt").exists()
    assert (production / "prod.marker").read_text(encoding="utf-8") == "REAL DATA"
    assert (production / "bot" / ".env").read_text(encoding="utf-8") == (
        "BOT_TOKEN=production"
    )
    assert (production / "version.txt").read_text(encoding="utf-8") == "9.9.9"


def _deploy(tmp_path, monkeypatch, *flags):
    source = tmp_path / "source"
    production = tmp_path / "production"
    _create_source(source)
    _create_production(production)
    monkeypatch.setattr(deploy, "SOURCE_DIR", source)
    monkeypatch.setattr(
        "sys.argv", ["deploy_to_prod.py", str(production), "--yes", *flags]
    )
    return deploy.main(), production


def test_restart_services_restarts_running_tasks(tmp_path, monkeypatch, scheduler):
    scheduler.states = {"SalaryAppWeb": "Running", "SalaryAppBot": "Running"}

    code, production = _deploy(tmp_path, monkeypatch, "--restart-services")

    assert code == 0
    assert scheduler.restarted == ["SalaryAppWeb", "SalaryAppBot"]
    assert (production / "version.txt").read_text(encoding="utf-8") == "9.9.9"


def test_restart_skips_missing_and_disabled_tasks(tmp_path, monkeypatch, scheduler):
    scheduler.states = {"SalaryAppBot": "Disabled"}  # SalaryAppWeb отсутствует

    code, _ = _deploy(tmp_path, monkeypatch, "--restart-services")

    assert code == 0
    assert scheduler.restarted == []


def test_failed_restart_is_reported_without_rollback(tmp_path, monkeypatch, scheduler):
    scheduler.states = {"SalaryAppWeb": "Running"}
    scheduler.restart_result = "Ready"  # задача не поднялась

    code, production = _deploy(tmp_path, monkeypatch, "--restart-services")

    assert code == 1
    # Код уже обновлён и проверен — откат из-за сервиса не нужен
    assert (production / "version.txt").read_text(encoding="utf-8") == "9.9.9"


def test_dry_run_with_restart_does_not_touch_tasks(tmp_path, monkeypatch, scheduler):
    scheduler.states = {"SalaryAppWeb": "Running", "SalaryAppBot": "Running"}

    code, production = _deploy(tmp_path, monkeypatch, "--dry-run", "--restart-services")

    assert code == 0
    assert scheduler.restarted == []
    assert (production / "old_code.txt").exists()


def test_without_flag_reminds_about_running_services(tmp_path, monkeypatch, scheduler, capsys):
    scheduler.states = {"SalaryAppWeb": "Running", "SalaryAppBot": "Ready"}

    code, _ = _deploy(tmp_path, monkeypatch)

    output = capsys.readouterr().out
    assert code == 0
    assert scheduler.restarted == []
    assert "СТАРЫЙ код" in output and "SalaryAppWeb" in output
    assert "Start-ScheduledTask SalaryAppBot" not in output  # бот не запущен — о нём не напоминаем
