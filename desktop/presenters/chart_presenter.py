from typing import Any, Dict, List
from core.utils.money import MoneyUtils
from core.utils.dates import DateUtils


class ChartPresenter:
    """Prepare chart-ready metadata without touching UI/tooling."""

    @staticmethod
    def _moving_average(values: List[float], window: int = 3) -> List[float]:
        if not values:
            return []
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            avg = sum(values[start:i + 1]) / (i - start + 1)
            result.append(avg)
        return result

    def prepare_monthly_dto(self, dto: Dict[str, Any]) -> Dict[str, Any]:
        items = dto.get("items", [])
        if not items:
            return {"has_data": False}

        period = dto.get("period")
        if period == "all":
            labels = [f"{DateUtils.get_month_name(i['month'], short=True)} {i['year']}" for i in items]
            values = [float(i.get("total", 0) or 0) for i in items]
            month_nums = [int(i.get("month")) for i in items]
            tick_positions = [idx for idx, m in enumerate(month_nums) if m in (1, 4, 7, 10)]
            tick_labels = [labels[i] for i in tick_positions] if tick_positions else labels
            return {
                "has_data": True,
                "is_all_years": True,
                "labels": labels,
                "values": values,
                "label": "Итого",
                "color": "#4BC0C0",
                "tick_positions": tick_positions,
                "tick_labels": tick_labels,
                "trend": self._moving_average(values, window=3),
                "trend_label": "Тренд (3 мес)"
            }

        labels = [DateUtils.get_month_name(i['month'], short=False) for i in items]
        advances = [float(i.get("advance", 0) or 0) for i in items]
        salaries = [float(i.get("salary", 0) or 0) for i in items]
        totals = [float(i.get("total", 0) or 0) for i in items]
        return {
            "has_data": True,
            "is_all_years": False,
            "labels": labels,
            "datasets": [
                {"label": "Аванс", "data": advances, "backgroundColor": "#FF6384"},
                {"label": "Зарплата", "data": salaries, "backgroundColor": "#36A2EB"},
                {"label": "Итого", "data": totals, "backgroundColor": "#4BC0C0"}
            ]
        }

    @staticmethod
    def prepare_yearly_dto(dto: Dict[str, Any]) -> Dict[str, Any]:
        items = dto.get("items", [])
        if not items:
            return {"has_data": False}
        labels = [str(item.get("year")) for item in items]
        values = [float(item.get("total", 0) or 0) for item in items]
        return {
            "has_data": True,
            "labels": labels,
            "values": values,
            "color": "#4A90E2"
        }

    @staticmethod
    def prepare_growth_dto(dto: Dict[str, Any]) -> Dict[str, Any]:
        items = dto.get("items", [])
        if len(items) < 2:
            return {"has_data": False}

        labels = []
        growth_rates = []
        for i in range(1, len(items)):
            prev = items[i - 1]
            curr = items[i]
            prev_total = float(prev.get("total", 0) or 0)
            curr_total = float(curr.get("total", 0) or 0)
            if prev_total > 0:
                growth = ((curr_total - prev_total) / prev_total) * 100
            else:
                growth = 0
            prev_label = f"{prev.get('year')}{'*' if prev.get('projected') else ''}"
            curr_label = f"{curr.get('year')}{'*' if curr.get('projected') else ''}"
            labels.append(f"{prev_label}-{curr_label}")
            growth_rates.append(round(growth, 2))

        note = "* — прогнозные данные, текущий год" if any(i.get("projected") for i in items) else None

        return {
            "has_data": True,
            "labels": labels,
            "values": growth_rates,
            "color": "#FF8C42",
            "fill_color": "#FF8C42",
            "note": note
        }

    @staticmethod
    def prepare_average_dto(dto: Dict[str, Any]) -> Dict[str, Any]:
        items = dto.get("items", [])
        months = [DateUtils.get_month_name(m, short=False) for m in range(1, 13)]
        avg_advance = [0.0] * 12
        avg_salary = [0.0] * 12
        avg_total = [0.0] * 12

        for item in items:
            idx = int(item.get("month", 0)) - 1
            if 0 <= idx < 12:
                avg_advance[idx] = float(item.get("avg_advance", 0) or 0)
                avg_salary[idx] = float(item.get("avg_salary", 0) or 0)
                avg_total[idx] = float(item.get("avg_total", 0) or 0)

        return {
            "has_data": True,
            "labels": months,
            "datasets": [
                {
                    "label": "Средний аванс",
                    "data": avg_advance,
                    "borderColor": "#FF6384",
                    "backgroundColor": "#FF6384",
                    "fill": False
                },
                {
                    "label": "Средняя зарплата",
                    "data": avg_salary,
                    "borderColor": "#36A2EB",
                    "backgroundColor": "#36A2EB",
                    "fill": False
                },
                {
                    "label": "Средний итог",
                    "data": avg_total,
                    "borderColor": "#4BC0C0",
                    "backgroundColor": "#4BC0C0",
                    "fill": False
                }
            ]
        }

    def prepare_kpi(
        self,
        summary: Dict[str, Any],
        best_month: Dict[str, Any],
        best_year: Dict[str, Any],
        selected_year: Any,
        show_best_year_always: bool,
        currency: str,
    ) -> Dict[str, Any]:
        total_amount = 0.0
        avg_monthly = 0.0
        records = 0
        first_year = None
        last_year = None

        if summary:
            total_amount = float(summary.get("total_all", 0) or 0)
            avg_monthly = float(summary.get("average_monthly", 0) or 0)
            records = int(summary.get("total_records", 0) or 0)
            first_year = summary.get("first_year")
            last_year = summary.get("last_year")

        if best_month:
            best_month_text = f"{best_month.get('month_name', '')} {best_month.get('year', '')}".strip()
            best_month_total = MoneyUtils.format_amount_plain(float(best_month.get('total', 0) or 0))
            best_month_value = f"{best_month_text} • {best_month_total}"
        else:
            best_month_value = "—"

        if best_year:
            best_year_text = str(best_year.get('year', '')).strip()
            best_year_total = MoneyUtils.format_amount_plain(float(best_year.get('total', 0) or 0))
            best_year_value = f"{best_year_text} • {best_year_total}"
        else:
            best_year_value = "—"

        if selected_year:
            period_value = str(selected_year)
        else:
            if first_year and last_year:
                period_value = f"{first_year}–{last_year}"
            else:
                period_value = "—"

        return {
            "total": MoneyUtils.format_kpi_amount(total_amount, currency),
            "avg": MoneyUtils.format_kpi_amount(avg_monthly, currency),
            "records": str(records),
            "best_month": best_month_value,
            "best_year": best_year_value,
            "period": period_value,
            "show_best_year": bool(show_best_year_always)
        }
