from copy import deepcopy
from unittest.mock import Mock

import pytest

from desktop.presenters.chart_presenter import ChartPresenter


@pytest.fixture(autouse=True)
def no_database_access(monkeypatch):
    monkeypatch.setattr(
        "core.database.connection.DatabaseConnection.get_connection",
        Mock(side_effect=AssertionError("Presenter must not access SQLite")),
    )


@pytest.mark.parametrize("period", ["year", "all"])
def test_monthly_tooltips_keep_values_and_input_unchanged(period):
    dto = {
        "period": period,
        "year": 2026 if period == "year" else None,
        "items": [
            {"year": 2026, "month": 3, "advance": 12345.67, "salary": 85000.5, "total": 97346.17},
            {"year": 2026, "month": 4, "advance": 0, "salary": 0, "total": 0},
        ],
    }
    original = deepcopy(dto)

    model = ChartPresenter().prepare_monthly_dto(dto)

    assert dto == original
    if period == "all":
        assert model["values"] == [97346.17, 0.0]
        assert model["tooltips"] == [
            "Март 2026\nИтого: 97 346,17 руб.",
            "Апрель 2026\nИтого: 0,00 руб.",
        ]
    else:
        advance, salary, total = model["datasets"]
        assert advance["data"] == [12345.67, 0.0]
        assert salary["data"] == [85000.5, 0.0]
        assert total["data"] == [97346.17, 0.0]
        assert advance["tooltips"][0] == "Март 2026\nАванс: 12 345,67 руб."
        assert salary["tooltips"][0] == "Март 2026\nЗарплата: 85 000,50 руб."
        assert total["tooltips"][1] == "Апрель 2026\nИтого: 0,00 руб."


def test_all_years_tooltips_distinguish_same_month_in_different_years():
    model = ChartPresenter().prepare_monthly_dto({
        "period": "all",
        "items": [
            {"year": 2025, "month": 3, "total": 100},
            {"year": 2026, "month": 3, "total": 200},
        ],
    })

    assert model["tooltips"] == [
        "Март 2025\nИтого: 100,00 руб.",
        "Март 2026\nИтого: 200,00 руб.",
    ]


def test_monthly_tooltips_empty_input_preserves_no_data_contract():
    assert ChartPresenter().prepare_monthly_dto({"items": []}) == {"has_data": False}
