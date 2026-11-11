"""Фоновая загрузка matplotlib и отложенная перерисовка скрытых графиков."""
import threading
from types import SimpleNamespace
from unittest.mock import Mock

from desktop.views.report.chart_backend import ChartBackendLoader
from desktop.views.report.report_view import CHART_TABS, ReportView, _redraw

BACKEND = ("canvas-class", "figure-class")


def test_loader_imports_on_demand_only_once():
    importer = Mock(return_value=BACKEND)
    loader = ChartBackendLoader(importer)

    assert loader.get() == BACKEND
    assert loader.get() == BACKEND
    importer.assert_called_once()


def test_loader_preloads_in_background_thread():
    threads = []

    def importer():
        threads.append(threading.current_thread())
        return BACKEND

    loader = ChartBackendLoader(importer)
    loader.start()
    loader.start()  # повторный запуск не создаёт второй поток

    assert loader.get() == BACKEND
    assert len(threads) == 1
    assert threads[0] is not threading.main_thread()


def test_loader_waits_for_unfinished_background_import():
    release = threading.Event()
    calls = []

    def importer():
        calls.append(1)
        release.wait(timeout=5)
        return BACKEND

    loader = ChartBackendLoader(importer)
    loader.start()
    threading.Timer(0.05, release.set).start()

    assert loader.get() == BACKEND
    assert len(calls) == 1  # дождались фонового импорта, а не начали второй


def test_loader_reports_missing_matplotlib():
    loader = ChartBackendLoader(Mock(return_value=None))
    loader.start()

    assert loader.get() is None


def test_loader_retries_in_main_thread_after_background_failure():
    importer = Mock(side_effect=[RuntimeError("broken install"), BACKEND])
    loader = ChartBackendLoader(importer)
    loader.start()

    assert loader.get() == BACKEND
    assert importer.call_count == 2


def _chart(visible: bool) -> dict:
    return {"canvas": Mock(), "dirty": False, "is_visible": lambda: visible}


def test_visible_chart_is_drawn_immediately():
    chart = _chart(visible=True)

    _redraw(chart)

    chart["canvas"].draw_idle.assert_called_once()
    assert chart["dirty"] is False


def test_hidden_chart_is_only_marked_for_redraw():
    chart = _chart(visible=False)

    _redraw(chart)

    chart["canvas"].draw_idle.assert_not_called()
    assert chart["dirty"] is True


def test_pending_chart_is_drawn_when_its_tab_opens():
    shown = {"monthly": True, "yearly": False}
    charts = {
        key: {"canvas": Mock(), "dirty": False, "is_visible": lambda key=key: shown[key]}
        for key in shown
    }
    view = SimpleNamespace(charts=charts)
    _redraw(charts["yearly"])  # данные обновились, пока вкладка скрыта

    ReportView._draw_pending_charts(view)
    charts["yearly"]["canvas"].draw_idle.assert_not_called()

    shown.update(monthly=False, yearly=True)  # перешли на вкладку «по годам»
    ReportView._draw_pending_charts(view)
    ReportView._draw_pending_charts(view)

    charts["yearly"]["canvas"].draw_idle.assert_called_once()
    charts["monthly"]["canvas"].draw_idle.assert_not_called()
    assert charts["yearly"]["dirty"] is False


def test_chart_tabs_cover_all_updated_charts():
    assert [spec.key for spec in CHART_TABS] == ["monthly", "yearly", "growth", "average"]
    assert [spec.key for spec in CHART_TABS if spec.bar_tooltip] == ["monthly"]
    assert [spec.key for spec in CHART_TABS if spec.zero_line] == ["growth"]
