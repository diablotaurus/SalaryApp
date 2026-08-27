"""Pure conversion helpers for exact persisted monetary values."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("999999999999.99")


def normalize_amount(value: Any, field_label: str = "сумма") -> float:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Некорректная {field_label}") from exc

    if not amount.is_finite():
        raise ValueError(f"{field_label.capitalize()} должна быть конечным числом")
    if amount < 0:
        raise ValueError(f"{field_label.capitalize()} не может быть отрицательной")
    if amount > MAX_AMOUNT:
        raise ValueError(f"{field_label.capitalize()} превышает допустимое значение")
    return float(amount.quantize(CENT, rounding=ROUND_HALF_UP))


def to_cents(value: Any) -> int:
    amount = Decimal(str(normalize_amount(value)))
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_cents(value: int | None) -> float:
    return float((Decimal(value or 0) / 100).quantize(CENT))
