from pathlib import Path

import scripts.deploy_to_prod as deploy


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
