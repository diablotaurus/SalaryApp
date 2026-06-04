import runpy
import sys
import types
import importlib


def test_run_web_entrypoint_calls_bootstrap_main(monkeypatch):
    called = {"ok": False}

    fake_bootstrap = types.ModuleType("web.bootstrap")

    def fake_main():
        called["ok"] = True

    fake_bootstrap.main = fake_main
    monkeypatch.setitem(sys.modules, "web.bootstrap", fake_bootstrap)

    runpy.run_module("run_web", run_name="__main__")
    assert called["ok"] is True


def test_run_bot_entrypoint_calls_asyncio_run(monkeypatch):
    called = {"ok": False}

    fake_bot_main = types.ModuleType("bot.main")

    async def fake_main():
        return None

    fake_bot_main.main = fake_main
    monkeypatch.setitem(sys.modules, "bot.main", fake_bot_main)

    import asyncio

    def fake_run(coro):
        called["ok"] = True
        coro.close()
        return None

    monkeypatch.setattr(asyncio, "run", fake_run)

    runpy.run_module("run_bot", run_name="__main__")
    assert called["ok"] is True


def test_desktop_app_importable_without_path_hacks():
    module = importlib.import_module("desktop.app")
    assert hasattr(module, "App")
