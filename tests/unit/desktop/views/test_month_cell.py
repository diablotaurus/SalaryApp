import pytest

from desktop.views.main.month_cell import TEXT_NO_DATA, MonthCell, MonthCellStyle


def _style(root, data_size=9):
    return MonthCellStyle.create(
        root,
        background="#dcdad5",
        title_size=10,
        data_size=data_size,
        total_size=10,
        advance_color="#0d6efd",
        salary_color="#198754",
        total_color="#dc3545",
    )


def _month(advance=20783.87, salary=84562.16, advance_date="28.01.2026", salary_date="13.02.2026"):
    return {
        "month_name": "Январь",
        "has_data": True,
        "advance": advance,
        "salary": salary,
        "advance_date": advance_date,
        "salary_date": salary_date,
        "total": advance + salary,
    }


def _texts(cell):
    return [cell.itemcget(item, "text") for item in cell.find_all() if cell.type(item) == "text"]


def _render(root, cell, width=300):
    cell.place(x=0, y=0, width=width, height=cell.winfo_reqheight())
    root.update_idletasks()
    cell._redraw()


def test_month_cell_draws_payments_and_total(root):
    cell = MonthCell(root, _month(), _style(root))
    _render(root, cell)

    texts = _texts(cell)
    assert texts[0] == "Январь"
    assert "Аванс" in texts and "Зарплата" in texts
    assert "28.01.2026" in texts and "13.02.2026" in texts
    assert any(text.startswith("Итого:") for text in texts)


def test_month_cell_skips_zero_payment_and_marks_missing_date(root):
    cell = MonthCell(root, _month(advance=0, salary_date=None), _style(root))
    _render(root, cell)

    texts = _texts(cell)
    assert "Аванс" not in texts
    assert "Зарплата" in texts
    assert "-" in texts


def test_month_cell_without_data_shows_placeholder(root):
    cell = MonthCell(root, {"month_name": "Октябрь", "has_data": False}, _style(root))
    _render(root, cell)

    assert _texts(cell) == ["Октябрь", TEXT_NO_DATA]


@pytest.mark.parametrize("data_size", [9, 12, 18])
def test_payment_rows_do_not_overlap_total(root, data_size):
    # Раньше на крупных шрифтах строка «Зарплата» обрезалась: зона выплат была ниже двух строк.
    cell = MonthCell(root, _month(), _style(root, data_size=data_size))
    _render(root, cell, width=600)

    def bbox_of(prefix):
        item = next(i for i in cell.find_all() if cell.type(i) == "text"
                    and cell.itemcget(i, "text").startswith(prefix))
        return cell.bbox(item)

    salary_bottom = bbox_of("Зарплата")[3]
    total_top = bbox_of("Итого:")[1]
    assert salary_bottom <= total_top
    assert bbox_of("Итого:")[3] <= cell.winfo_height()
