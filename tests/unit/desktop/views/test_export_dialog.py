import pytest

from desktop.controllers.main_tab_controller import MainTabController
from desktop.views.dialogs.export_dialog import ExportDialog


@pytest.mark.parametrize(
    ("default_format", "selected"),
    [("excel", "excel"), ("json", "json"), ("csv", "csv"), ("xml", "csv")],
)
def test_export_dialog_opens_on_default_format(root, default_format, selected):
    # Раньше окно всегда открывалось на CSV, настройка «Формат экспорта» не влияла
    dialog = ExportDialog(root, controller=None, default_format=default_format)
    try:
        assert dialog.format_var.get() == selected
    finally:
        dialog.destroy()


def test_default_export_format_comes_from_settings(monkeypatch):
    monkeypatch.setattr(
        "desktop.controllers.main_tab_controller.SettingsAPI.get_setting",
        lambda key, default=None: {"success": True, "data": {"key": key, "value": "excel"}},
    )

    assert MainTabController._default_export_format() == "excel"


def test_default_export_format_falls_back_to_csv(monkeypatch):
    def broken(*_args, **_kwargs):
        raise OSError("db locked")

    monkeypatch.setattr("desktop.controllers.main_tab_controller.SettingsAPI.get_setting", broken)

    assert MainTabController._default_export_format() == "csv"
