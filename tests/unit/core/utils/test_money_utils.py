import pytest

from core.utils.money import MoneyUtils


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12345.67", 12345.67),
        ("12 345.67", 12345.67),
        ("12345,67", 12345.67),
        ("12 345,67", 12345.67),
        ("", 0.0),
        ("abc", 0.0),
    ],
)
def test_parse_amount(raw, expected):
    assert MoneyUtils.parse_amount(raw) == expected


def test_format_amount_plain():
    assert MoneyUtils.format_amount_plain(12345.6) == "12 345.60"

