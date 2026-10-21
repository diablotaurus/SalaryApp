"""
Графики для Telegram картинкой (PNG).

matplotlib загружается только при построении (импорт ~0.5 с не замедляет
запуск бота), рисование — через Figure + Agg, без pyplot и GUI: так безопасно
строить график в отдельном потоке (asyncio.to_thread) и не держать окна.
"""
from __future__ import annotations

from io import BytesIO
from typing import Iterable

from core.utils.dates import DateUtils

CURRENT_COLOR = "#0d6efd"   # синий, как аванс в приложении
PREVIOUS_COLOR = "#adb5bd"  # серый — прошлый год
AVERAGE_COLOR = "#198754"   # зелёный, как зарплата
WIDTH, HEIGHT, DPI = 9, 4.8, 120


def _thousands(value: float, _position: int = 0) -> str:
    """Подпись оси: «120 тыс.» (ноль — просто «0»)."""
    if not value:
        return "0"
    return f"{value / 1000:,.0f}".replace(",", " ") + " тыс."


def _png(figure) -> bytes:
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    FigureCanvasAgg(figure)
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=DPI, bbox_inches="tight")
    return buffer.getvalue()


def _new_axes(title: str):
    from matplotlib.figure import Figure
    from matplotlib.ticker import FuncFormatter

    figure = Figure(figsize=(WIDTH, HEIGHT))
    axes = figure.add_subplot()
    axes.set_title(title, fontsize=13, fontweight="bold")
    axes.yaxis.set_major_formatter(FuncFormatter(_thousands))
    axes.grid(axis="y", alpha=0.3)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    return figure, axes


def _month_totals(years: dict[int, dict], year: int) -> list[float]:
    months = {m["month"]: m for m in years.get(year, {}).get("months", [])}
    return [float(months.get(month, {}).get("total") or 0) for month in range(1, 13)]


def year_chart(years_data: Iterable[dict], year: int) -> bytes:
    """Помесячно: выбранный год против прошлого (если он есть)."""
    years = {int(item["year"]): item for item in years_data}
    current = _month_totals(years, year)
    has_previous = (year - 1) in years
    title = f"{year} и {year - 1} по месяцам" if has_previous else f"{year} по месяцам"
    figure, axes = _new_axes(title)

    positions = range(12)
    width = 0.4 if has_previous else 0.6
    if has_previous:
        axes.bar([p - width / 2 for p in positions], _month_totals(years, year - 1), width,
                 color=PREVIOUS_COLOR, label=str(year - 1))
        axes.bar([p + width / 2 for p in positions], current, width, color=CURRENT_COLOR, label=str(year))
        axes.legend(frameon=False)
    else:
        axes.bar(list(positions), current, width, color=CURRENT_COLOR)
    axes.set_xticks(list(positions))
    axes.set_xticklabels([DateUtils.get_month_name(m, short=True) for m in range(1, 13)])
    return _png(figure)


def years_chart(years_data: Iterable[dict]) -> bytes:
    """По годам: среднемесячный доход (сравним и для неполного года) с подписями."""
    items = sorted(({"year": int(i["year"]), **i["summary"]} for i in years_data), key=lambda i: i["year"])
    figure, axes = _new_axes("Среднемесячный доход по годам")
    labels = [str(item["year"]) for item in items]
    averages = [float(item["average_monthly"] or 0) for item in items]
    bars = axes.bar(labels, averages, 0.6, color=AVERAGE_COLOR)
    for bar, value in zip(bars, averages):
        axes.annotate(
            f"{value:,.0f}".replace(",", " "),
            (bar.get_x() + bar.get_width() / 2, value),
            ha="center", va="bottom", fontsize=9, xytext=(0, 3), textcoords="offset points",
        )
    return _png(figure)
