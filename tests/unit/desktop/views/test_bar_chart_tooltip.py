from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from desktop.presenters.chart_presenter import ChartPresenter
from desktop.views.report.bar_chart_tooltip import BarChartTooltip
from desktop.views.report.chart_constants import TOOLTIP_MARGIN_PX
from desktop.views.report.report_view import ReportView


@pytest.fixture(autouse=True)
def no_database_access(monkeypatch):
    monkeypatch.setattr(
        "core.database.connection.DatabaseConnection.get_connection",
        Mock(side_effect=AssertionError("Chart tooltip must not access SQLite")),
    )


@pytest.fixture
def chart():
    figure = Figure(figsize=(8, 4.7), dpi=100)
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    tooltip = BarChartTooltip(axes, canvas)
    view = SimpleNamespace(
        presenter=ChartPresenter(),
        charts={"monthly": {"fig": figure, "ax": axes, "canvas": canvas, "tooltip": tooltip}},
    )
    yield view, axes, canvas, tooltip
    tooltip.disconnect()
    figure.clear()


def hover(canvas, bar, x_fraction=0.5, y_fraction=0.5):
    box = bar.get_window_extent()
    event = MouseEvent(
        "motion_notify_event", canvas,
        box.x0 + box.width * x_fraction,
        box.y0 + box.height * y_fraction,
    )
    canvas.callbacks.process("motion_notify_event", event)
    return event


@pytest.mark.parametrize("bar_index, label", [(0, "Аванс"), (1, "Зарплата"), (2, "Итого")])
def test_grouped_chart_tooltip_matches_hovered_series(chart, bar_index, label):
    view, axes, canvas, tooltip = chart
    ReportView.update_monthly_chart(view, {
        "period": "year", "year": 2026,
        "items": [{"year": 2026, "month": 3, "advance": 100, "salary": 200, "total": 300}],
    })

    hover(canvas, axes.patches[bar_index])

    assert tooltip._annotation.get_visible()
    assert tooltip._annotation.get_text() == f"Март 2026\n{label}: {(bar_index + 1) * 100},00 руб."


@pytest.mark.parametrize("event_name", ["axes_leave_event", "figure_leave_event", "resize_event"])
def test_tooltip_hides_on_leave_and_resize(chart, event_name):
    _, axes, canvas, tooltip = chart
    bars = axes.bar([0], [100])
    tooltip.set_items([(bars[0], "March 2026\nTotal: 100.00")])
    canvas.draw()
    hover(canvas, bars[0])

    canvas.callbacks.process(event_name, Event(event_name, canvas))

    assert not tooltip._annotation.get_visible()
    assert tooltip._active_bar is None


def test_tooltip_hides_over_empty_plot_without_repeated_redraws(chart, monkeypatch):
    _, axes, canvas, tooltip = chart
    bars = axes.bar([0], [100])
    tooltip.set_items([(bars[0], "Total: 100.00")])
    axes.set_xlim(-2, 2)
    canvas.draw()
    draw = Mock()
    monkeypatch.setattr(canvas, "draw_idle", draw)
    event = hover(canvas, bars[0])
    canvas.callbacks.process("motion_notify_event", event)
    assert draw.call_count == 1

    x, y = axes.transData.transform((1.5, 50))
    event = MouseEvent("motion_notify_event", canvas, x, y)
    canvas.callbacks.process("motion_notify_event", event)
    canvas.callbacks.process("motion_notify_event", event)

    assert not tooltip._annotation.get_visible()
    assert draw.call_count == 2


@pytest.mark.parametrize("empty_data", [None, {}, {"items": []}])
def test_refresh_clears_old_bars_annotations_and_empty_data(chart, empty_data):
    view, axes, canvas, tooltip = chart
    connections = list(tooltip._connections)
    for year in (2025, 2026, 2025):
        ReportView.update_monthly_chart(view, {
            "period": "all",
            "items": [{"year": year, "month": 3, "total": 100}],
        })
        assert len(axes.patches) == 1
        assert len(axes.texts) == 1
        assert not tooltip._annotation.get_visible()
        hover(canvas, axes.patches[0])
        assert tooltip._annotation.get_text() == f"Март {year}\nИтого: 100,00 руб."
        assert tooltip._connections == connections

    ReportView.update_monthly_chart(view, empty_data)

    assert tooltip._annotation is None
    assert not tooltip._items
    canvas.callbacks.process("motion_notify_event", MouseEvent("motion_notify_event", canvas, 100, 100))
    assert tooltip._annotation is None


def test_clear_after_external_axes_reset_is_safe(chart):
    _, axes, canvas, tooltip = chart
    bars = axes.bar([0], [1])
    tooltip.set_items([(bars[0], "Old data")])
    canvas.draw()
    hover(canvas, bars[0])
    axes.clear()

    tooltip.clear()
    tooltip.set_items([])

    assert tooltip._annotation is None
    assert not tooltip._items


@pytest.mark.parametrize("close_event", [False, True])
def test_disconnect_releases_callbacks_and_is_idempotent(chart, close_event):
    _, axes, canvas, tooltip = chart
    bar = axes.bar([0], [1])[0]
    tooltip.set_items([(bar, "One")])
    connections = list(tooltip._connections)

    if close_event:
        canvas.callbacks.process("close_event", Event("close_event", canvas))
    else:
        tooltip.disconnect()
    tooltip.disconnect()
    tooltip.set_items([(bar, "Must not reconnect")])

    assert not tooltip._connections
    assert tooltip._annotation is None
    for callbacks in canvas.callbacks.callbacks.values():
        assert all(connection not in callbacks for connection in connections)


@pytest.mark.parametrize("size, dpi", [((3.2, 2.4), 100), ((8, 4.7), 100), ((12, 7), 144)])
@pytest.mark.parametrize("corner", [(0.02, 0.02), (0.98, 0.02), (0.02, 0.98), (0.98, 0.98)])
def test_tooltip_box_stays_within_canvas(chart, size, dpi, corner):
    _, axes, canvas, tooltip = chart
    figure = axes.figure
    figure.set_size_inches(*size)
    figure.set_dpi(dpi)
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99)
    bar = axes.bar([0.5], [1], width=1)[0]
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    tooltip.set_items([(bar, "Сентябрь 2026\nЗарплата: 999 999 999 999.99 руб.")])
    canvas.draw()

    hover(canvas, bar, *corner)

    assert tooltip._annotation.get_visible()
    bounds = tooltip._annotation.get_bbox_patch().get_window_extent(canvas.get_renderer())
    assert bounds.x0 >= TOOLTIP_MARGIN_PX - 0.5
    assert bounds.y0 >= TOOLTIP_MARGIN_PX - 0.5
    assert bounds.x1 <= figure.bbox.x1 - TOOLTIP_MARGIN_PX + 0.5
    assert bounds.y1 <= figure.bbox.y1 - TOOLTIP_MARGIN_PX + 0.5


def test_hidden_and_zero_bars_do_not_break_hover(chart):
    _, axes, canvas, tooltip = chart
    bars = axes.bar([0, 1], [0, 100])
    tooltip.set_items([(bars[0], "Zero"), (bars[1], "Hidden")])
    canvas.draw()
    bars[1].set_visible(False)

    hover(canvas, bars[1])
    assert not tooltip._annotation.get_visible()
    hover(canvas, bars[0])
    if tooltip._annotation.get_visible():
        assert tooltip._annotation.get_text() == "Zero"


@pytest.mark.parametrize("widget_exists", [True, False])
def test_widget_bindings_are_owned_and_released_by_tooltip(chart, widget_exists):
    _, axes, canvas, _ = chart
    widget = Mock()
    widget.bind.side_effect = ["destroy-binding", "unmap-binding"]
    widget.winfo_exists.return_value = widget_exists
    tooltip = BarChartTooltip(axes, canvas, widget)
    assert widget.bind.call_args_list == [
        call("<Destroy>", tooltip.disconnect, add="+"),
        call("<Unmap>", tooltip._hide, add="+"),
    ]

    tooltip.disconnect()
    tooltip.disconnect()

    if widget_exists:
        assert widget.unbind.call_args_list == [
            call("<Destroy>", "destroy-binding"),
            call("<Unmap>", "unmap-binding"),
        ]
    else:
        widget.unbind.assert_not_called()
    assert not tooltip._bindings
    assert tooltip._widget is None
