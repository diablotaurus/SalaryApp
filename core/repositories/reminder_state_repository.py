"""
Состояние напоминаний Telegram-бота о вводе выплат.

Хранится в таблице settings под служебными ключами (без отдельной таблицы
и миграции). SettingsService такие ключи не знает и в настройках не показывает.
"""
from __future__ import annotations

import json
from datetime import date

from core.repositories.settings_repository import SettingsRepository

LAST_SENT_KEY = "reminders.last_sent"
SNOOZED_KEY = "reminders.snoozed"
SNOOZE_KEEP_MONTHS = 6  # старые отметки «не напоминать» удаляются


class ReminderStateRepository:
    """День последней отправки (дата по МСК) и выплаты, о которых не напоминать."""

    @staticmethod
    def get_last_sent() -> date | None:
        value = SettingsRepository.get_setting(LAST_SENT_KEY)
        try:
            return date.fromisoformat(value) if value else None
        except ValueError:
            return None

    @staticmethod
    def set_last_sent(day: date) -> None:
        SettingsRepository.set_setting(LAST_SENT_KEY, day.isoformat())

    @staticmethod
    def get_snoozed() -> frozenset[tuple[str, int, int]]:
        """Выплаты (вид, год, месяц), о которых пользователь попросил не напоминать."""
        raw = SettingsRepository.get_setting(SNOOZED_KEY)
        try:
            items = json.loads(raw) if raw else []
            return frozenset((str(kind), int(year), int(month)) for kind, year, month in items)
        except (TypeError, ValueError):
            return frozenset()

    @staticmethod
    def add_snoozed(kind: str, year: int, month: int, today: date) -> None:
        oldest = today.year * 12 + today.month - SNOOZE_KEEP_MONTHS
        items = {
            item
            for item in ReminderStateRepository.get_snoozed() | {(kind, year, month)}
            if item[1] * 12 + item[2] >= oldest
        }
        SettingsRepository.set_setting(SNOOZED_KEY, json.dumps(sorted(items)))
