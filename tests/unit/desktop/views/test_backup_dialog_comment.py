import pytest

from desktop.views.dialogs.backup_dialog import BackupDialog


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("auto_on_close", "Автокопия при закрытии"),  # служебная метка — понятным текстом
        ("Перед отпуском\nвторая строка", "Перед отпуском вторая строка"),  # в одну строку
        ("Автоматическая копия перед восстановлением", "Автоматическая копия перед восстановлением"),
        (None, ""),
        ("", ""),
    ],
)
def test_backup_comment_is_formatted_for_list(raw, shown):
    assert BackupDialog._format_comment(raw) == shown
