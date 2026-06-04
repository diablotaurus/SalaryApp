from core.utils.dates import DateUtils


def test_get_month_name_and_number_roundtrip():
    assert DateUtils.get_month_name(1) == "Январь"
    assert DateUtils.get_month_number("Январь") == 1
    assert DateUtils.get_month_number("январь") == 1


def test_get_next_month_handles_year_boundary():
    assert DateUtils.get_next_month(2025, 12) == (2026, 1)
    assert DateUtils.get_next_month(2025, 6) == (2025, 7)


def test_get_previous_month_handles_year_boundary():
    assert DateUtils.get_previous_month(2025, 1) == (2024, 12)
    assert DateUtils.get_previous_month(2025, 6) == (2025, 5)

