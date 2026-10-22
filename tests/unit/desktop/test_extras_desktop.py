from types import SimpleNamespace

from desktop.presenters.chart_presenter import ChartPresenter
from desktop.views.dialogs.extra_payment_dialog import ExtraPaymentDialog
from desktop.views.main.month_cell import MonthCell, MonthCellStyle


def _style(root):
    return MonthCellStyle.create(root, "#dcdad5", 10, 9, 10, "#0d6efd", "#198754", "#dc3545")


def _month(**extra):
    return {
        "month_name": "Август", "has_data": True, "advance": 1000.0, "salary": 2000.0,
        "advance_date": "28.08.2026", "salary_date": "14.09.2026", "total": 3000.0, **extra,
    }


def _texts(cell):
    return [cell.itemcget(item, "text") for item in cell.find_all() if cell.type(item) == "text"]


def _render(root, cell):
    cell.place(x=0, y=0, width=300, height=cell.winfo_reqheight())
    root.update_idletasks()
    cell._redraw()


def test_month_cell_shows_extras_row_and_tooltip(root):
    extras = [{"kind_name": "Отпускные", "amount": 35000.0, "paid_date": "10.08.2026", "comment": "отпуск"}]
    plain = MonthCell(root, _month(), _style(root))
    with_extras = MonthCell(root, _month(extras_total=35000.0, extras=extras, note="больничный"), _style(root))
    _render(root, plain)
    _render(root, with_extras)

    assert "Доп." not in _texts(plain)
    assert {"Доп.", "35 000,00"} <= set(_texts(with_extras))
    assert with_extras.winfo_reqheight() > plain.winfo_reqheight()  # третья строка
    assert with_extras._tooltip_text == "✎ больничный\nОтпускные: 35 000,00 • 10.08.2026 — отпуск"


def test_year_chart_gets_extras_series_only_when_present():
    items = [{"year": 2026, "month": m, "advance": 1.0, "salary": 2.0, "extras": 0.0, "total": 3.0} for m in (7, 8)]
    plain = ChartPresenter().prepare_monthly_dto({"period": "year", "items": items})
    items[1] = {**items[1], "extras": 5.0, "total": 8.0}
    with_extras = ChartPresenter().prepare_monthly_dto({"period": "year", "items": items})

    assert [d["label"] for d in plain["datasets"]] == ["Аванс", "Зарплата", "Итого"]
    assert [d["label"] for d in with_extras["datasets"]] == ["Аванс", "Зарплата", "Доп. выплаты", "Итого"]
    assert with_extras["datasets"][2]["data"] == [0.0, 5.0]


def test_kpi_average_title_mentions_regular_income_only_with_extras():
    def kpi(summary):
        return ChartPresenter().prepare_kpi(summary, None, None, None, True, "руб.")

    base = {"total_all": 1.0, "average_monthly": 120000.0, "total_records": 1}
    assert kpi(base)["avg_title"] == "Среднемесячно"
    with_extras = kpi({**base, "total_extras": 40000.0, "regular_average_monthly": 107798.43})
    assert with_extras["avg_title"] == "Среднемесячно · регулярный 108 000"


def test_extra_payment_dialog_saves_parsed_amount(root):
    calls, saved = [], []
    controller = SimpleNamespace(add_extra_payment=lambda *args: calls.append(args) or True)
    dialog = ExtraPaymentDialog(root, controller, 2026, 8, on_saved=lambda: saved.append(True))
    dialog.kind_var.set("Отпускные")
    dialog.amount_var.set("35 000,50")
    dialog.date_var.set("10.08.2026")

    dialog._save()

    assert calls == [(2026, 8, "vacation", 35000.5, "10.08.2026", None)]
    assert saved == [True]
