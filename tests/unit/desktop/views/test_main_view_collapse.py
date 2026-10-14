from types import SimpleNamespace

from desktop.views.constants import ARROW_YEAR_COLLAPSED, ARROW_YEAR_EXPANDED
from desktop.views.main.main_view import MainView
from desktop.views.main.month_cell import MonthCell


def _controller():
    noop = lambda *_args, **_kwargs: None  # noqa: E731
    return SimpleNamespace(
        add_data=noop, refresh_history=noop, export_history=noop,
        show_backups=noop, edit_year=noop, delete_year=noop,
    )


def _month(m):
    return {
        "month_name": f"М{m}", "has_data": True,
        "advance": 1000.0, "salary": 2000.0, "total": 3000.0,
        "advance_date": "01.01.2026", "salary_date": "15.01.2026",
    }


def _year(year):
    return {
        "year": year,
        "summary": {"total": 1000.0, "average_monthly": 100.0, "months_with_data": 12},
        "months": [_month(m) for m in range(1, 13)],
    }


def _years(*years):
    return [_year(year) for year in years]


def _month_cells(widget):
    found = 1 if isinstance(widget, MonthCell) else 0
    return found + sum(_month_cells(child) for child in widget.winfo_children())


def _cells_of(view, year):
    return _month_cells(view._year_cards[year]["body"])


def _view(root, layout="standard"):
    view = MainView(root, _controller())
    view.apply_settings({"history_layout_mode": layout})
    return view


def _columns(view):
    """Годы в каждой колонке сверху вниз."""
    card_to_year = {str(entry["card"]): year for year, entry in view._year_cards.items()}
    return [
        [card_to_year[str(card)] for card in column.pack_slaves()]
        for column in view._card_columns
    ]


def test_only_default_year_is_expanded_and_built(root):
    view = _view(root)

    view.display_years(_years(2024, 2025, 2026), default_expanded_year=2026)

    assert _cells_of(view, 2026) == 12
    assert _cells_of(view, 2025) == 0  # свёрнутый год не строит сетку месяцев
    assert _cells_of(view, 2024) == 0
    assert view._year_cards[2026]["arrow"].cget("text") == ARROW_YEAR_EXPANDED
    assert view._year_cards[2025]["arrow"].cget("text") == ARROW_YEAR_COLLAPSED


def test_toggle_builds_months_once_and_hides_them(root):
    view = _view(root)
    view.display_years(_years(2025, 2026), default_expanded_year=2026)

    view._toggle_year(2025)
    assert _cells_of(view, 2025) == 12
    assert view._year_cards[2025]["body"].winfo_manager() == "pack"

    view._toggle_year(2025)
    assert view._year_cards[2025]["body"].winfo_manager() == ""  # скрыт
    assert _cells_of(view, 2025) == 12  # сетка не пересоздаётся при повторном разворачивании


def test_user_choice_survives_redraw(root):
    view = _view(root)
    view.display_years(_years(2025, 2026), default_expanded_year=2026)
    view._toggle_year(2025)  # развернул прошлый год
    view._toggle_year(2026)  # свернул текущий

    # Перерисовка после сохранения данных / смены настроек
    view.display_years(_years(2025, 2026), default_expanded_year=2026)

    assert _cells_of(view, 2025) == 12
    assert _cells_of(view, 2026) == 0


def test_new_default_year_expands_when_it_first_appears(root):
    # Январь: данных за новый год ещё нет — развёрнут последний год с данными.
    view = _view(root)
    view.display_years(_years(2025, 2026), default_expanded_year=2026)

    # Внесли первые данные за 2027 — он появляется сразу развёрнутым.
    view.display_years(_years(2025, 2026, 2027), default_expanded_year=2027)

    assert _cells_of(view, 2027) == 12
    assert _cells_of(view, 2026) == 12  # выбор по 2026 не изменился


def test_standard_layout_keeps_single_column_in_year_order(root):
    view = _view(root)

    view.display_years(_years(2020, 2023, 2024, 2025, 2026), default_expanded_year=2026)

    assert _columns(view) == [[2026, 2025, 2024, 2023, 2020]]


def test_quarterly_layout_stacks_collapsed_years_next_to_expanded(root):
    # Сценарий со скриншота: развёрнутый 2026 слева, свёрнутые годы — по порядку
    # в правой колонке, без пустот под 2025.
    view = _view(root, layout="quarterly")

    view.display_years(_years(2020, 2023, 2024, 2025, 2026), default_expanded_year=2026)

    assert _columns(view) == [[2026], [2025, 2024, 2023, 2020]]


def test_toggled_card_stays_in_its_column(root):
    view = _view(root, layout="quarterly")
    view.display_years(_years(2020, 2023, 2024, 2025, 2026), default_expanded_year=2026)

    view._toggle_year(2024)  # разворачиваем год из правой колонки

    left, right = _columns(view)
    assert 2024 in right
    assert right[:2] == [2025, 2024]  # годы выше кликнутого не сдвинулись
    # порядок лет сверху вниз внутри колонок сохраняется
    assert left == sorted(left, reverse=True) and right == sorted(right, reverse=True)


def test_wheel_does_not_shift_content_that_fits(root):
    # Если содержимое короче окна, Tk разрешал двигать его внутри окна:
    # колёсико вверх сдвигало карточки вниз, оставляя пустоту сверху.
    root.geometry("1600x1400")
    view = _view(root)
    view.pack(fill="both", expand=True)
    view.display_years(_years(2025, 2026), default_expanded_year=2026)
    # Окно нужно показать: у скрытого окна холст имеет высоту 1 px,
    # и «короткого» содержимого не бывает.
    root.deiconify()
    try:
        root.update()
        assert view.canvas.winfo_height() > view.cards_container.winfo_reqheight()

        for delta in (120, 120, 120, -120, -120):
            view._on_mouse_scroll(SimpleNamespace(delta=delta))
        root.update()

        assert view.canvas.canvasy(0) == 0
        assert view.scrollbar.grid_info() == {}  # прокручивать нечего — полосы нет
    finally:
        root.withdraw()


def test_month_grid_receives_mouse_wheel_after_lazy_build(root):
    view = _view(root)
    view.display_years(_years(2025, 2026), default_expanded_year=2026)

    view._toggle_year(2025)

    cell = next(
        widget for widget in view._year_cards[2025]["body"].winfo_children()[-1].winfo_children()
        if isinstance(widget, MonthCell)
    )
    assert cell.bind("<MouseWheel>")  # прокрутка колесиком работает и над новыми ячейками
