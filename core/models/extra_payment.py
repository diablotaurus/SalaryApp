"""
Дополнительная выплата: отпускные, премия, больничные, прочее.

Относится к месяцу получения (как пришла на карту). Месяц может иметь
несколько доп. выплат; в итог месяца они входят вместе с авансом и
зарплатой, а «регулярный доход» считается без них.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.utils.dates import DateUtils

# Код вида -> подпись (порядок — как в списках выбора)
EXTRA_KINDS = {
    "vacation": "Отпускные",
    "bonus": "Премия",
    "sick": "Больничные",
    "other": "Прочее",
}


@dataclass
class ExtraPayment:
    year: int
    month: int
    kind: str
    amount: float
    paid_date: Optional[datetime] = None  # календарная дата получения
    comment: Optional[str] = None
    id: Optional[int] = None

    @property
    def kind_name(self) -> str:
        return EXTRA_KINDS.get(self.kind, self.kind)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "year": self.year,
            "month": self.month,
            "kind": self.kind,
            "kind_name": self.kind_name,
            "amount": self.amount,
            "paid_date": DateUtils.format_date(self.paid_date) if self.paid_date else "",
            "comment": self.comment or "",
        }
