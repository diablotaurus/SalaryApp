from types import SimpleNamespace

from desktop.views.settings.settings_view import SettingsView


def _view(root, saved):
    controller = SimpleNamespace(save_settings=lambda settings: saved.update(settings))
    return SettingsView(root, controller)


def test_telegram_reminders_switch_is_loaded_and_saved(root):
    saved = {}
    view = _view(root, saved)

    view.update_settings({"telegram_reminders": "0"})
    assert view.settings_vars["telegram_reminders"].get() is False

    view.settings_vars["telegram_reminders"].set(True)
    view._save_settings()
    assert saved["telegram_reminders"] is True


def test_date_format_setting_is_gone(root):
    # Настройка убрана в 1.2.30: ни на что не влияла
    assert "date_format" not in _view(root, {}).settings_vars
