"""
Доп. выплаты (отпускные, премии, больничные, прочее): проверка и сохранение.

Выплата относится к месяцу получения. Если записи этого месяца ещё нет,
создаётся пустая (аванс и зарплата 0): месяц появляется в истории, а
напоминания о выплатах и правило «месяц учитывается в средних, когда
выплачена зарплата» работают как раньше. Пустой месяц без доп. выплат
и заметки удаляется вместе с последней доп. выплатой.
"""
from __future__ import annotations

from typing import List, Optional

from core.models.extra_payment import EXTRA_KINDS, ExtraPayment
from core.repositories.extra_payment_repository import ExtraPaymentRepository
from core.repositories.salary_repository import SalaryRepository
from core.services.salary_service import SalaryService
from core.utils.money_values import normalize_amount


class ExtraPaymentService:
    @staticmethod
    def add(
        year: int,
        month: int,
        kind: str,
        amount: float,
        paid_date: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> ExtraPayment:
        """
        Добавить доп. выплату.

        Raises:
            ValueError: Неизвестный вид, сумма не больше нуля, неверная дата,
                комментарий длиннее допустимого
        """
        year, month = SalaryService._validate_period(year, month)
        if kind not in EXTRA_KINDS:
            raise ValueError(f"Неизвестный вид доп. выплаты: {kind}")
        amount = normalize_amount(amount, "сумма доп. выплаты")
        if amount <= 0:
            raise ValueError("Сумма доп. выплаты должна быть больше нуля")
        payment = ExtraPayment(
            year=year,
            month=month,
            kind=kind,
            amount=amount,
            paid_date=SalaryService.parse_payment_date(paid_date, "даты доп. выплаты"),
            comment=SalaryService.normalize_note(comment),
        )
        SalaryRepository.ensure_month(year, month)
        return ExtraPaymentRepository.add(payment)

    @staticmethod
    def delete(payment_id: int) -> bool:
        """Удалить доп. выплату; опустевший месяц (0/0, без заметки) убирается из истории."""
        payment = ExtraPaymentRepository.get(int(payment_id))
        if payment is None:
            return False
        ExtraPaymentRepository.delete(payment.id)
        SalaryRepository.delete_if_empty(payment.year, payment.month)
        return True

    @staticmethod
    def get_by_month(year: int, month: int) -> List[ExtraPayment]:
        return ExtraPaymentRepository.get_by_month(year, month)

    @staticmethod
    def get_by_year(year: int) -> List[ExtraPayment]:
        return ExtraPaymentRepository.get_by_year(year)

    @staticmethod
    def get_all() -> List[ExtraPayment]:
        return ExtraPaymentRepository.get_all()
