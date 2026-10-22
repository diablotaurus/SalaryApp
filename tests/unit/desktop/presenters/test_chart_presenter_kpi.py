from desktop.presenters.chart_presenter import ChartPresenter


def _kpi(forecast):
    return ChartPresenter().prepare_kpi(
        {"total_all": 1.0, "average_monthly": 1.0, "total_records": 1}, None, None, None, True, "руб.", forecast
    )


def test_kpi_shows_forecast_for_current_year():
    model = _kpi({"year": 2026, "forecast": 1289512.4})

    assert model["forecast_title"] == "Прогноз на 2026"
    assert model["forecast"] == "≈ 1 290 000 руб."


def test_kpi_forecast_cell_empty_without_forecast():
    model = _kpi(None)

    assert (model["forecast_title"], model["forecast"]) == ("", "")
