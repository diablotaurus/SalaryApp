from datetime import datetime, timedelta, timezone

import pytest

from core.models.salary import Salary
from core.models.year import is_payment_complete
from core.utils import clock
from core.utils.clock import MOSCOW_TZ, as_utc, format_moscow, parse_utc, to_moscow
from core.utils.dates import DateUtils


def _freeze_utc(monkeypatch, moment: datetime) -> None:
    monkeypatch.setattr(clock, "utc_now", lambda: moment)


def test_utc_moment_is_shown_in_moscow_with_label():
    moment = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)

    assert format_moscow(moment) == "15.07.2026 12:30 МСК"
    assert format_moscow(moment, label=False) == "15.07.2026 12:30"


def test_21_utc_belongs_to_next_moscow_day():
    moment = datetime(2026, 10, 14, 21, 0, tzinfo=timezone.utc)

    assert to_moscow(moment).date() == datetime(2026, 10, 15).date()
    assert format_moscow(moment) == "15.10.2026 00:00 МСК"


@pytest.mark.parametrize(
    "text",
    [
        "2026-07-15T09:30:00Z",
        "2026-07-15T09:30:00+00:00",
        "2026-07-15T12:30:00+03:00",
        "2026-07-15 09:30:00",  # SQLite CURRENT_TIMESTAMP: UTC без метки пояса
    ],
)
def test_parse_utc_gives_same_moment_for_any_notation(text):
    parsed = parse_utc(text)

    assert parsed == datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
    assert parsed.utcoffset() == timedelta(0)


def test_naive_value_is_treated_as_utc_by_documented_rule():
    assert as_utc(datetime(2026, 1, 1, 12, 0)) == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_now_helpers_are_timezone_aware():
    assert clock.utc_now().utcoffset() == timedelta(0)
    assert clock.moscow_now().tzinfo == MOSCOW_TZ


def test_current_period_switches_at_moscow_midnight(monkeypatch):
    # 31 декабря 21:30 UTC — в Москве уже 1 января следующего года
    _freeze_utc(monkeypatch, datetime(2026, 12, 31, 21, 30, tzinfo=timezone.utc))

    assert DateUtils.get_current_period() == (2027, 1)


def test_salary_paid_today_by_moscow_date_counts_after_moscow_midnight():
    # Зарплата 15.10 (календарная дата); 14.10 21:30 UTC = 15.10 00:30 МСК
    record = Salary(year=2026, month=10, advance=1.0, salary=2.0, salary_date=datetime(2026, 10, 15))
    just_after_midnight = to_moscow(datetime(2026, 10, 14, 21, 30, tzinfo=timezone.utc))
    just_before_midnight = to_moscow(datetime(2026, 10, 14, 20, 30, tzinfo=timezone.utc))

    assert is_payment_complete(record, just_after_midnight) is True
    assert is_payment_complete(record, just_before_midnight) is False


def test_new_salary_record_gets_utc_created_at():
    assert Salary(year=2026, month=1).created_at.utcoffset() == timedelta(0)
