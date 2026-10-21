"""
Единый стандарт времени SalaryApp: хранить и считать в UTC, показывать в МСК.

Полное описание — GLOBAL_TIME_STANDARD_RU.md в корне MyHobby. Здесь собраны
все переходы между шкалами, чтобы остальной код не работал с часовыми
поясами напрямую.

Правило для значений без часового пояса (naive):
    в этом проекте это время SQLite CURRENT_TIMESTAMP (created_at, updated_at,
    applied_at), а SQLite всегда пишет его в UTC. Поэтому naive-значение
    трактуется как UTC и получает метку часового пояса при чтении.

Календарные даты (даты аванса и зарплаты) — не моменты времени и между
часовыми поясами не конвертируются. С ними сравнивается «сегодня» по МСК.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
MSK_LABEL = "МСК"
DISPLAY_FORMAT = "%d.%m.%Y %H:%M"


def utc_now() -> datetime:
    """Текущий момент в UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def moscow_now() -> datetime:
    """Текущий момент по МСК (timezone-aware) — для «текущего месяца/года»."""
    return utc_now().astimezone(MOSCOW_TZ)


def moscow_today() -> date:
    """Текущая календарная дата по МСК."""
    return moscow_now().date()


def as_utc(value: datetime) -> datetime:
    """Привести момент к UTC; naive-значение считается UTC (см. описание модуля)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_utc(text: str) -> datetime:
    """
    Разобрать ISO 8601 в момент UTC.

    Принимает «Z» и любое смещение («+00:00», «+03:00»); строка без смещения
    (формат SQLite CURRENT_TIMESTAMP) считается UTC.
    """
    return as_utc(datetime.fromisoformat(str(text).strip()))


def to_moscow(value: datetime) -> datetime:
    """Перевести момент в МСК для показа человеку."""
    return as_utc(value).astimezone(MOSCOW_TZ)


def format_moscow(value: datetime, fmt: str = DISPLAY_FORMAT, *, label: bool = True) -> str:
    """
    Момент для человека: время по МСК, по умолчанию с подписью.

    Пример: 2026-10-14 21:38 UTC -> «15.10.2026 00:38 МСК».
    label=False — когда «МСК» уже указано в заголовке колонки.
    """
    text = to_moscow(value).strftime(fmt)
    return f"{text} {MSK_LABEL}" if label else text
