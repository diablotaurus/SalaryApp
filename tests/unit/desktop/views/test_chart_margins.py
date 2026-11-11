"""Левое поле графиков: подпись оси Y не уходит за край в нешироком окне."""
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from desktop.views.report.chart_constants import CHART_MARGIN_LEFT, CHART_MIN_LEFT_INCH
from desktop.views.report.report_view import _fit_margins, left_margin


def test_wide_chart_keeps_usual_margin():
    assert left_margin(19.0) == CHART_MARGIN_LEFT


def test_narrow_chart_gets_minimum_margin_in_inches():
    assert left_margin(10.0) * 10.0 == pytest.approx(CHART_MIN_LEFT_INCH)


def test_unknown_width_falls_back_to_usual_margin():
    assert left_margin(0) == CHART_MARGIN_LEFT


# Ширина холста в пикселях и масштаб экрана: 100 % (dpi 100), 125 % и 150 %
@pytest.mark.parametrize("width_px", [1000, 1300, 1900])
@pytest.mark.parametrize("dpi", [100, 125, 150])
def test_y_axis_label_fits_with_six_digit_ticks(width_px, dpi):
    figure = Figure(figsize=(width_px / dpi, 5), dpi=dpi)
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    axes.bar(range(12), [165_000] * 12)  # деления вида «160000», как на «Зарплате по месяцам»
    axes.set_ylabel("Сумма, руб.")

    _fit_margins(figure)
    canvas.draw()

    assert axes.yaxis.label.get_window_extent().x0 >= 0
