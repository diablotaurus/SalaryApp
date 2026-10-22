"""Read-only aggregate queries for salary analytics."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.database.connection import DatabaseConnection


class AnalyticsRepository:
    """Persistence boundary for aggregate salary queries."""

    @staticmethod
    def get_yearly_totals(*, ascending: bool = False) -> List[Dict[str, Any]]:
        order = "ASC" if ascending else "DESC"
        conn = DatabaseConnection.get_connection()
        rows = conn.execute(
            f"""
            SELECT year,
                   SUM(advance) / 100.0 AS total_advance,
                   SUM(salary) / 100.0 AS total_salary,
                   SUM(extras_total) / 100.0 AS total_extras,
                   SUM(advance + salary + extras_total) / 100.0 AS total,
                   COUNT(*) AS months_count
            FROM month_totals
            GROUP BY year
            ORDER BY year {order}
            """
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_best_month() -> Optional[Dict[str, Any]]:
        conn = DatabaseConnection.get_connection()
        row = conn.execute(
            """
            SELECT year, month, SUM(advance + salary + extras_total) / 100.0 AS total
            FROM month_totals
            GROUP BY year, month
            ORDER BY total DESC, year DESC, month DESC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_best_year() -> Optional[Dict[str, Any]]:
        conn = DatabaseConnection.get_connection()
        row = conn.execute(
            """
            SELECT year, SUM(advance + salary + extras_total) / 100.0 AS total
            FROM month_totals
            GROUP BY year
            ORDER BY total DESC, year DESC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_statistics(year: Optional[int] = None) -> Dict[str, Any]:
        conn = DatabaseConnection.get_connection()
        where = "WHERE year = ?" if year is not None else ""
        params = (year,) if year is not None else ()
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS total_records,
                   SUM(advance) / 100.0 AS total_advance_all,
                   SUM(salary) / 100.0 AS total_salary_all,
                   SUM(extras_total) / 100.0 AS total_extras_all,
                   MIN(year) AS first_year,
                   MAX(year) AS last_year
            FROM month_totals
            {where}
            """,
            params,
        ).fetchone()
        stats = dict(row)
        yearly = AnalyticsRepository.get_yearly_totals()
        if year is not None:
            yearly = [item for item in yearly if int(item["year"]) == year]
        stats["by_year"] = [
            {
                "year": item["year"],
                "advance": item["total_advance"],
                "salary": item["total_salary"],
                "extras": item["total_extras"],
                "months": item["months_count"],
            }
            for item in yearly
        ]
        return stats
