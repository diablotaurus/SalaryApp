"""
Тексты годовых отчётов бота: сводка года, подробно по месяцам, итоги по годам.

Данные приходят из SalaryAPI.get_all_grouped_by_year (среднемесячное там
считается по единому правилу — только месяцы с выплаченной зарплатой),
здесь они только раскладываются в текст.
"""
from __future__ import annotations

from typing import Any, Optional

from core.services.statistics_service import StatisticsService
from core.utils.money import MoneyUtils

LAST_MONTHS_SHOWN = 3


def _amount(value: Any) -> str:
    return MoneyUtils.format_amount_plain(float(value or 0))


def _percent(value: Optional[float]) -> str:
    """«+4,8 %», «−2,1 %»; None — пусто."""
    if value is None:
        return ""
    sign = "+" if value >= 0 else "−"
    return f"{sign}{abs(value):.1f} %".replace(".", ",")


def _by_year(years_data: list[dict]) -> dict[int, dict]:
    return {int(item["year"]): item for item in years_data}


def _average_change(years: dict[int, dict], year: int) -> Optional[float]:
    """Изменение среднемесячного к предыдущему году (сравнимо и для неполного года)."""
    if year not in years or year - 1 not in years:
        return None
    return StatisticsService.percent_change(
        years[year]["summary"]["average_monthly"], years[year - 1]["summary"]["average_monthly"]
    )


def format_year_overview(years_data: list[dict], year: int) -> str:
    """Короткая сводка года: итог, среднее и его изменение, последние месяцы."""
    years = _by_year(years_data)
    if year not in years:
        return f"📅 {year} год\n\nДанных пока нет."

    summary = years[year]["summary"]
    change = _average_change(years, year)
    average_line = f"Среднемесячно: {_amount(summary['average_monthly'])}"
    if change is not None:
        average_line += f" ({_percent(change)} к {year - 1})"

    lines = [
        f"📅 {year} год",
        "",
        f"Итого: {_amount(summary['total'])}",
        average_line,
        f"Месяцев с данными: {summary['months_with_data']}",
    ]
    filled = [month for month in years[year]["months"] if month.get("has_data")]
    if filled:
        lines += ["", "Последние месяцы:"]
        for month in sorted(filled, key=lambda item: item["month"], reverse=True)[:LAST_MONTHS_SHOWN]:
            lines.append(f"• {month['month_name']} — {_amount(month['total'])}")
    return "\n".join(lines)


def format_year_details(years_data: list[dict], year: int) -> str:
    """Подробно по месяцам: аванс и зарплата с датами, итог месяца и года."""
    years = _by_year(years_data)
    filled = [month for month in years.get(year, {}).get("months", []) if month.get("has_data")]
    if not filled:
        return f"Нет данных за {year} год."

    blocks = [f"Статистика за {year} год"]
    for month in sorted(filled, key=lambda item: item["month"]):
        blocks.append("\n".join([
            str(month["month_name"]),
            f"  Аванс: {_amount(month['advance'])}  •  {month.get('advance_date') or '-'}",
            f"  Зарплата: {_amount(month['salary'])}  •  {month.get('salary_date') or '-'}",
            f"  Итого: {_amount(month['total'])}",
        ]))
    blocks.append(f"Итого за год: {_amount(years[year]['summary']['total'])}")
    return "\n\n".join(blocks)


def format_years_summary(years_data: list[dict]) -> str:
    """Итоги по всем годам: сумма, число месяцев, среднее и его изменение к прошлому году."""
    years = _by_year(years_data)
    if not years:
        return "📆 Данных пока нет. Внесите первый месяц: /add"

    lines = ["📆 Итоги по годам", ""]
    for year in sorted(years, reverse=True):
        summary = years[year]["summary"]
        lines.append(f"{year} — {_amount(summary['total'])} ({summary['months_with_data']} мес.)")
        detail = f"   в среднем {_amount(summary['average_monthly'])} в месяц"
        change = _average_change(years, year)
        if change is not None:
            detail += f", {_percent(change)} к {year - 1}"
        lines.append(detail)
    total = sum(float(item["summary"]["total"] or 0) for item in years.values())
    lines += ["", f"Всего за {len(years)} {_years_word(len(years))}: {_amount(total)}"]
    return "\n".join(lines)


def _years_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "год"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "года"
    return "лет"


def format_month_comparison(comparison: Optional[dict]) -> Optional[str]:
    """Строка после сохранения месяца: выше/ниже среднего за последний год."""
    if not comparison or comparison.get("percent") is None:
        return None
    percent = comparison["percent"]
    average = _amount(comparison["average"])
    if abs(percent) < 1:
        return f"📊 На уровне среднего за последние 12 месяцев ({average})."
    direction = "выше" if percent > 0 else "ниже"
    arrow = "📈" if percent > 0 else "📉"
    value = f"{abs(percent):.0f}"
    return f"{arrow} На {value} % {direction} среднего за последние 12 месяцев ({average})."
