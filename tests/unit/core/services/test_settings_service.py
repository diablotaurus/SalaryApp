import pytest

from core.exceptions import ValidationError
from core.services.settings_service import SettingsService


def test_get_all_settings_merges_defaults(temp_db):
    settings = SettingsService.get_all_settings()

    assert settings["currency"] == "руб."
    assert settings["history_layout_mode"] == "standard"
    assert settings["backup_days"] == "30"


def test_set_settings_is_validated_and_normalized(temp_db):
    saved = SettingsService.set_settings(
        {"backup_auto": True, "backup_days": 14, "total_color": "#ABCDEF"}
    )

    assert saved == {
        "backup_auto": "1",
        "backup_days": "14",
        "total_color": "#abcdef",
    }


def test_set_settings_does_not_partially_save_invalid_batch(temp_db):
    before = SettingsService.get_setting("currency")

    with pytest.raises(ValidationError):
        SettingsService.set_settings({"currency": "USD", "backup_days": 0})

    assert SettingsService.get_setting("currency") == before


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("unknown", "value"),
        ("backup_days", 0),
        ("month_data_font_size", 40),
        ("advance_color", "red"),
        ("export_format", "xml"),
        ("date_format", "%d.%m.%Y"),  # настройка убрана: ни на что не влияла
    ],
)
def test_rejects_unsupported_or_invalid_settings(temp_db, key, value):
    with pytest.raises(ValidationError):
        SettingsService.set_setting(key, value)
