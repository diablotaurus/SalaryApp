from datetime import datetime

import pytest

from core.services.salary_service import SalaryService


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01012025", "01.01.2025"),
        ("01.01.2025", "01.01.2025"),
        ("01/01/2025", "01.01.2025"),
        ("01-01-2025", "01.01.2025"),
    ],
)
def test_normalize_date_input_supported_formats(raw, expected):
    assert SalaryService._normalize_date_input(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "1.1.2025"])
def test_normalize_date_input_invalid(raw):
    assert SalaryService._normalize_date_input(raw) is None


def test_parse_payment_date_valid():
    parsed = SalaryService.parse_payment_date("31.12.2025", "даты")
    assert isinstance(parsed, datetime)
    assert parsed.strftime("%d.%m.%Y") == "31.12.2025"


def test_parse_payment_date_invalid_date_raises_value_error():
    with pytest.raises(ValueError):
        SalaryService.parse_payment_date("31.02.2025", "даты")
