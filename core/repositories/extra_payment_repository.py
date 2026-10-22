"""Хранение доп. выплат (таблица extra_payments, суммы — в копейках)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from core.database.connection import DatabaseConnection
from core.models.extra_payment import ExtraPayment
from core.utils.money_values import from_cents, to_cents


class ExtraPaymentRepository:
    @staticmethod
    def add(payment: ExtraPayment) -> ExtraPayment:
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute(
            """
            INSERT INTO extra_payments (year, month, kind, amount, paid_date, comment)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            (
                payment.year,
                payment.month,
                payment.kind,
                to_cents(payment.amount),
                payment.paid_date.date().isoformat() if payment.paid_date else None,
                payment.comment,
            ),
        )
        row = cursor.fetchone()
        conn.commit()
        return ExtraPaymentRepository._row_to_payment(row)

    @staticmethod
    def get(payment_id: int) -> Optional[ExtraPayment]:
        conn = DatabaseConnection.get_connection()
        row = conn.execute("SELECT * FROM extra_payments WHERE id = ?", (payment_id,)).fetchone()
        return ExtraPaymentRepository._row_to_payment(row) if row else None

    @staticmethod
    def delete(payment_id: int) -> bool:
        conn = DatabaseConnection.get_connection()
        cursor = conn.execute("DELETE FROM extra_payments WHERE id = ?", (payment_id,))
        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def get_by_month(year: int, month: int) -> List[ExtraPayment]:
        conn = DatabaseConnection.get_connection()
        rows = conn.execute(
            "SELECT * FROM extra_payments WHERE year = ? AND month = ? ORDER BY paid_date, id",
            (year, month),
        ).fetchall()
        return [ExtraPaymentRepository._row_to_payment(row) for row in rows]

    @staticmethod
    def get_by_year(year: int) -> List[ExtraPayment]:
        conn = DatabaseConnection.get_connection()
        rows = conn.execute(
            "SELECT * FROM extra_payments WHERE year = ? ORDER BY month, paid_date, id", (year,)
        ).fetchall()
        return [ExtraPaymentRepository._row_to_payment(row) for row in rows]

    @staticmethod
    def get_all() -> List[ExtraPayment]:
        conn = DatabaseConnection.get_connection()
        rows = conn.execute(
            "SELECT * FROM extra_payments ORDER BY year DESC, month DESC, paid_date, id"
        ).fetchall()
        return [ExtraPaymentRepository._row_to_payment(row) for row in rows]

    @staticmethod
    def _row_to_payment(row) -> ExtraPayment:
        return ExtraPayment(
            id=row["id"],
            year=row["year"],
            month=row["month"],
            kind=row["kind"],
            amount=from_cents(row["amount"]),
            paid_date=datetime.fromisoformat(row["paid_date"]) if row["paid_date"] else None,
            comment=row["comment"],
        )
