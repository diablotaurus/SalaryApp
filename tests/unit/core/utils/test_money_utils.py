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
        ("   ", 0.0),
        ("87 432,71", 87432.71),   # неразрывный пробел (копирование из банка)
        ("87 432,71", 87432.71),   # узкий неразрывный пробел
        ("12,345.67", 12345.67),        # запятая — тысячи, точка — дробь
        ("12.345,67", 12345.67),        # точка — тысячи, запятая — дробь
        ("1,234,567.89", 1234567.89),
        ("100", 100.0),
        ("0,5", 0.5),
        ("-500", -500.0),               # знак сохраняется: отрицательные отсекает вызывающий код
    ],
)
def test_parse_amount(raw, expected):
    assert MoneyUtils.parse_amount(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "abc",
        "87432,7l",     # опечатка
        "87.432.71",    # непонятно, где дробная часть
        "12,345",       # три знака после разделителя — вероятно, тысячи
        "87.432",
        "1e3",
        "nan",
        "inf",
        "+500",
    ],
)
def test_parse_amount_rejects_ambiguous_or_invalid_input(raw):
    # Раньше такие значения молча превращались в 0 и затирали сумму в базе.
    with pytest.raises(ValueError):
        MoneyUtils.parse_amount(raw)


def test_parse_amount_error_names_the_field():
    with pytest.raises(ValueError, match="аванс «87432,7l»"):
        MoneyUtils.parse_amount("87432,7l", "аванс")


def test_format_amount_plain():
    assert MoneyUtils.format_amount_plain(12345.6) == "12 345,60"
