"""
Ячейка месяца на главной вкладке, нарисованная на одном Canvas.

Раньше ячейка собиралась из ~11 виджетов (рамки и подписи), и при нескольких
годах истории Tk тратил около секунды на показ вкладки. Один Canvas на ячейку
выглядит так же, но показывается в разы быстрее.

Раскладка повторяет прежнюю (tk.Label в pack/grid), поэтому отступы ниже
воспроизводят внутренние поля tk.Label и параметры упаковки старой версии.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.utils.money import MoneyUtils
from desktop.views.constants import FONT_MONTH_NO_DATA
from desktop.widgets.tooltip import Tooltip

FONT_FAMILY = "Segoe UI"
TEXT_NO_DATA = "Нет данных"
NO_DATA_COLOR = "gray"
BORDER_COLOR = "black"
EXTRAS_LABEL = "Доп."     # строка доп. выплат (отпускные, премии…)
EXTRAS_COLOR = "#6f42c1"
NOTE_MARK = "✎"           # значок заметки в правом верхнем углу ячейки
NOTE_MARK_COLOR = "#6c757d"
NOTE_MARK_PAD = 4

BORDER = 1                # Рамка ячейки (relief="solid", borderwidth=1)
LABEL_PAD = 3             # Поле tk.Label вокруг текста: padx/pady=1 + borderwidth=2
TITLE_PADY = (2, 1)       # Отступы названия месяца
PAYMENTS_PADX = 4         # Боковые отступы таблицы выплат
PAYMENTS_MIN_HEIGHT = 44  # Минимальная высота зоны выплат
PAYMENTS_PADY_BOTTOM = 2  # Отступ под таблицей выплат
TOTAL_PADY = (3, 2)       # Отступы строки «Итого»
DATE_PADX = (2, 1)        # Отступы колонки даты
AMOUNT_PADX = (1, 1)      # Отступы колонки суммы
NAME_MIN_WIDTH = 54       # Минимальные ширины колонок таблицы выплат
DATE_MIN_WIDTH = 52
AMOUNT_MIN_WIDTH = 56

PaymentRow = Tuple[str, str, str, str]  # (название, дата, сумма, цвет)


@dataclass(frozen=True)
class MonthCellStyle:
    """Общие для всех ячеек шрифты и цвета (создаются один раз на отрисовку)."""

    background: str
    title_font: tkfont.Font
    data_font: tkfont.Font
    total_font: tkfont.Font
    no_data_font: tkfont.Font
    advance_color: str
    salary_color: str
    total_color: str

    @classmethod
    def create(
        cls,
        root: tk.Misc,
        background: str,
        title_size: int,
        data_size: int,
        total_size: int,
        advance_color: str,
        salary_color: str,
        total_color: str,
    ) -> "MonthCellStyle":
        return cls(
            background=background,
            title_font=tkfont.Font(root=root, family=FONT_FAMILY, size=title_size, weight="bold"),
            data_font=tkfont.Font(root=root, family=FONT_FAMILY, size=data_size),
            total_font=tkfont.Font(root=root, family=FONT_FAMILY, size=total_size, weight="bold"),
            no_data_font=tkfont.Font(root=root, font=FONT_MONTH_NO_DATA),
            advance_color=advance_color,
            salary_color=salary_color,
            total_color=total_color,
        )

    @property
    def data_cell_height(self) -> int:
        """
        Высота ячейки с авансом и зарплатой. По ней выравниваются все строки
        сетки месяцев: иначе строка из «Нет данных» ниже, развёрнутые годы
        разной высоты, и свёрнутые карточки под ними встают «лесенкой».
        """
        return _cell_height(self, self.payments_area_height)

    @property
    def payments_area_height(self) -> int:
        """
        Фиксированная высота зоны выплат (2 строки), чтобы «Итого» не прыгало.

        Считается по реальной высоте строки шрифта: прежняя формула от размера
        в пунктах занижала высоту на крупных шрифтах, и строка «Зарплата» обрезалась.
        """
        return max(PAYMENTS_MIN_HEIGHT, 2 * _text_height(self.data_font))


def _text_height(font: tkfont.Font) -> int:
    """Высота строки так, как её занимает tk.Label с этим шрифтом."""
    return int(font.metrics("linespace")) + 2 * LABEL_PAD


def _title_bottom(style: "MonthCellStyle") -> int:
    return BORDER + TITLE_PADY[0] + _text_height(style.title_font) + TITLE_PADY[1]


def _cell_height(style: "MonthCellStyle", payments_height: int) -> int:
    """Высота ячейки с данными: название, зона выплат, «Итого»."""
    return (
        _title_bottom(style)
        + payments_height + PAYMENTS_PADY_BOTTOM
        + TOTAL_PADY[0] + _text_height(style.total_font) + TOTAL_PADY[1]
        + BORDER
    )


class MonthCell(tk.Canvas):
    """Ячейка месяца: название, строки «Аванс»/«Зарплата» и «Итого» (или «Нет данных»)."""

    def __init__(
        self,
        parent: tk.Misc,
        month_info: Dict[str, Any],
        style: MonthCellStyle,
        on_click: Optional[Callable[[], None]] = None,
    ):
        """
        Args:
            on_click: Действие по клику — открыть месяц для ввода и правки
                (в том числе пустой месяц «Нет данных»)
        """
        self._style = style
        self._title = str(month_info["month_name"])
        self._has_data = bool(month_info["has_data"])
        self._rows = self._build_rows(month_info, style) if self._has_data else []
        self._total_text = (
            f"Итого: {MoneyUtils.format_amount(month_info['total'], '')}" if self._has_data else ""
        )
        self._note = str(month_info.get("note") or "")
        self._tooltip_text = self._build_tooltip(self._note, month_info.get("extras") or [])

        super().__init__(
            parent,
            bg=style.background,
            highlightthickness=0,
            borderwidth=0,
            width=self._natural_width(),
            height=self._natural_height(),
            cursor="hand2" if on_click else "",
        )
        self.bind("<Configure>", self._redraw)
        if on_click:
            self.bind("<Button-1>", lambda _event: on_click(), add="+")
        if self._tooltip_text:
            Tooltip(self, self._tooltip_text)

    @staticmethod
    def _build_rows(month_info: Dict[str, Any], style: MonthCellStyle) -> List[PaymentRow]:
        rows: List[PaymentRow] = []
        payments = (
            ("Аванс", month_info["advance"], month_info.get("advance_date"), style.advance_color),
            ("Зарплата", month_info["salary"], month_info.get("salary_date"), style.salary_color),
        )
        for name, amount, date, color in payments:
            if amount > 0:
                rows.append((name, date or "-", MoneyUtils.format_amount(amount, ""), color))
        extras = float(month_info.get("extras_total") or 0)
        if extras > 0:
            rows.append((EXTRAS_LABEL, "", MoneyUtils.format_amount(extras, ""), EXTRAS_COLOR))
        return rows

    @staticmethod
    def _build_tooltip(note: str, extras: List[Dict[str, Any]]) -> str:
        """Подсказка при наведении: заметка и состав доп. выплат."""
        lines = [f"✎ {note}"] if note else []
        for payment in extras:
            line = f"{payment['kind_name']}: {MoneyUtils.format_amount_plain(payment['amount'])}"
            if payment.get("paid_date"):
                line += f" • {payment['paid_date']}"
            if payment.get("comment"):
                line += f" — {payment['comment']}"
            lines.append(line)
        return "\n".join(lines)

    def _payments_height(self) -> int:
        """Зона выплат: две строки, как у всех ячеек; третья — только при доп. выплатах."""
        return max(self._style.payments_area_height, len(self._rows) * _text_height(self._style.data_font))

    # --- Размеры ---------------------------------------------------------

    def _natural_columns(self) -> Tuple[int, int, int]:
        """Естественные ширины колонок «название | дата | сумма» (как у grid)."""
        font = self._style.data_font
        name_w = max([NAME_MIN_WIDTH] + [font.measure(r[0]) + 2 * LABEL_PAD for r in self._rows])
        date_w = max([DATE_MIN_WIDTH] + [
            font.measure(r[1]) + 2 * LABEL_PAD + sum(DATE_PADX) for r in self._rows
        ])
        amount_w = max([AMOUNT_MIN_WIDTH] + [
            font.measure(r[2]) + 2 * LABEL_PAD + sum(AMOUNT_PADX) for r in self._rows
        ])
        return name_w, date_w, amount_w

    def _natural_width(self) -> int:
        style = self._style
        widths = [style.title_font.measure(self._title) + 2 * LABEL_PAD]
        if self._has_data:
            widths.append(style.total_font.measure(self._total_text) + 2 * LABEL_PAD)
            widths.append(sum(self._natural_columns()) + 2 * PAYMENTS_PADX)
        else:
            widths.append(style.no_data_font.measure(TEXT_NO_DATA) + 2 * LABEL_PAD)
        return max(widths) + 2 * BORDER

    def _title_bottom(self) -> int:
        return _title_bottom(self._style)

    def _natural_height(self) -> int:
        style = self._style
        if not self._has_data:
            return self._title_bottom() + _text_height(style.no_data_font) + BORDER
        return _cell_height(style, self._payments_height())

    # --- Отрисовка -------------------------------------------------------

    def _draw_centered(self, text: str, font: tkfont.Font, label_top: int, width: int, **options: Any) -> None:
        """Текст по центру ячейки — в тех же целых координатах, что у tk.Label в pack."""
        label_width = font.measure(text) + 2 * LABEL_PAD
        label_left = BORDER + (width - 2 * BORDER - label_width) // 2
        self.create_text(
            label_left + LABEL_PAD, label_top + LABEL_PAD,
            text=text, font=font, anchor="nw", **options,
        )

    def _redraw(self, _event: Any = None) -> None:
        style = self._style
        width, height = self.winfo_width(), self.winfo_height()
        self.delete("all")
        self.create_rectangle(0, 0, width - 1, height - 1, outline=BORDER_COLOR)

        self._draw_centered(self._title, style.title_font, BORDER + TITLE_PADY[0], width)
        if self._note:
            self.create_text(
                width - BORDER - NOTE_MARK_PAD, BORDER + TITLE_PADY[0] + LABEL_PAD,
                text=NOTE_MARK, font=style.data_font, fill=NOTE_MARK_COLOR, anchor="ne",
            )

        top = self._title_bottom()
        if not self._has_data:
            # «Нет данных» — по центру оставшегося под названием места
            free_height = height - BORDER - top
            label_top = top + (free_height - _text_height(style.no_data_font)) // 2
            self._draw_centered(TEXT_NO_DATA, style.no_data_font, label_top, width, fill=NO_DATA_COLOR)
            return

        self._draw_payments(top, width)

        total_top = height - BORDER - TOTAL_PADY[1] - _text_height(style.total_font)
        self._draw_centered(self._total_text, style.total_font, total_top, width, fill=style.total_color)

    def _draw_payments(self, top: int, width: int) -> None:
        """Строки выплат: название слева, дата и сумма — по правому краю своих колонок."""
        font = self._style.data_font
        left = BORDER + PAYMENTS_PADX
        available = width - 2 * (BORDER + PAYMENTS_PADX)

        name_w, date_w, amount_w = self._natural_columns()
        extra = available - (name_w + date_w + amount_w)
        if extra > 0:
            # Как grid: свободное место поровну делят колонки даты и суммы (weight=1).
            date_w += extra // 2
            amount_w += extra - extra // 2

        date_right = left + name_w + date_w - DATE_PADX[1] - LABEL_PAD
        amount_right = left + name_w + date_w + amount_w - AMOUNT_PADX[1] - LABEL_PAD
        row_h = _text_height(font)

        for index, (name, date, amount, color) in enumerate(self._rows):
            text_top = top + index * row_h + LABEL_PAD
            self.create_text(left + LABEL_PAD, text_top, text=name, font=font, fill=color, anchor="nw")
            self.create_text(date_right, text_top, text=date, font=font, fill=color, anchor="ne")
            self.create_text(amount_right, text_top, text=amount, font=font, fill=color, anchor="ne")
