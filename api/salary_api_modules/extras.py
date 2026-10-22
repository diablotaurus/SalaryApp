"""Доп. выплаты (отпускные, премии, больничные, прочее)."""
from __future__ import annotations

from api.common import execute_with_default_error, failure, success
from core.models.extra_payment import EXTRA_KINDS
from core.services.extra_payment_service import ExtraPaymentService


def get_extra_kinds() -> dict:
    return success([{"kind": kind, "name": name} for kind, name in EXTRA_KINDS.items()])


def add_extra_payment(
    year: int,
    month: int,
    kind: str,
    amount: float,
    paid_date: str | None = None,
    comment: str | None = None,
) -> dict:
    try:
        payment = ExtraPaymentService.add(year, month, kind, amount, paid_date, comment)
    except ValueError as exc:
        return failure(str(exc), error="invalid")
    return success(payment.to_dict(), message="Доп. выплата сохранена")


def delete_extra_payment(payment_id: int) -> dict:
    def _action() -> dict:
        if ExtraPaymentService.delete(payment_id):
            return success(message="Доп. выплата удалена")
        return failure("Доп. выплата не найдена", error="not found")

    return execute_with_default_error(_action, "Ошибка при удалении доп. выплаты")


def get_extra_payments(year: int, month: int) -> dict:
    def _action() -> dict:
        payments = [payment.to_dict() for payment in ExtraPaymentService.get_by_month(year, month)]
        return success(payments, count=len(payments))

    return execute_with_default_error(_action, "Ошибка при получении доп. выплат")
