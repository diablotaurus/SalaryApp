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
                   SUM(advance + salary) / 100.0 AS total,
                   COUNT(*) AS months_count
            FROM salaries
            GROUP BY year
            ORDER BY year {order}
            """
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_monthly_averages(year: Optional[int] = None) -> Dict[str, Any]:
        conn = DatabaseConnection.get_connection()
        where = "WHERE year = ?" if year is not None else ""
        params = (year,) if year is not None else ()
        row = conn.execute(
            f"""
            SELECT AVG(advance) / 100.0 AS avg_advance,
                   AVG(salary) / 100.0 AS avg_salary,
                   AVG(advance + salary) / 100.0 AS avg_total
            FROM salaries
            {where}
            """,
            params,
        ).fetchone()
        result = dict(row)
        result["year"] = year if year is not None else "all"
        return result

    @staticmethod
    def get_average_by_month() -> List[Dict[str, Any]]:
        conn = DatabaseConnection.get_connection()
        rows = conn.execute(
            """
            SELECT month,
                   AVG(advance) / 100.0 AS avg_advance,
                   AVG(salary) / 100.0 AS avg_salary,
                   AVG(advance + salary) / 100.0 AS avg_total
            FROM salaries
            GROUP BY month
            ORDER BY month
            """
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_best_month() -> Optional[Dict[str, Any]]:
        conn = DatabaseConnection.get_connection()
        row = conn.execute(
            """
            SELECT year, month, SUM(advance + salary) / 100.0 AS total
            FROM salaries
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
            SELECT year, SUM(advance + salary) / 100.0 AS total
            FROM salaries
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
                   MIN(year) AS first_year,
                   MAX(year) AS last_year
            FROM salaries
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
                "months": item["months_count"],
            }
            for item in yearly
        ]
        return stats
