from desktop.controllers.main_tab_controller import MainTabController
from desktop.controllers.report_tab_controller import ReportTabController
from desktop.controllers.settings_tab_controller import SettingsTabController


class _DummyView:
    def __init__(self):
        self.years = None
        self.settings = None
        self.charts = []
        self.kpi_args = None
        self.display_calls = 0
        self.selected_year = None
        self.built = False

    def ensure_built(self):
        self.built = True

    def display_years(self, data, default_expanded_year=None):
        self.display_calls += 1
        self.years = data
        self.default_expanded_year = default_expanded_year

    def update_statistics(self, data):
        self.stats = data

    def update_years_list(self, years):
        assert self.built, "вкладка должна быть построена до обновления"
        self.years = years

    def get_selected_year(self):
        return self.selected_year

    def update_monthly_chart(self, data):
        self.charts.append(("m", data))

    def update_yearly_chart(self, data):
        self.charts.append(("y", data))

    def update_growth_chart(self, data):
        self.charts.append(("g", data))

    def update_average_chart(self, data):
        self.charts.append(("a", data))

    def update_kpi(self, *args, **kwargs):
        self.kpi_args = (args, kwargs)

    def update_settings(self, settings):
        self.settings = settings


class _DummyApp:
    def __init__(self):
        self.main_view = _DummyView()
        self.report_view = _DummyView()
        self.settings_view = _DummyView()


class _DummyNav:
    def __init__(self):
        self.app = _DummyApp()
        self.messages = []
        self.refreshed_history = False
        self.refreshed_reports = False

    def show_message(self, title, message, msg_type):
        self.messages.append((title, message, msg_type))
        if msg_type == "question":
            return True
        return None

    def refresh_history(self):
        self.refreshed_history = True

    def refresh_reports(self):
        self.refreshed_reports = True


def test_main_tab_controller_refresh_history(monkeypatch):
    nav = _DummyNav()
    controller = MainTabController(nav)

    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.get_all_grouped_by_year",
        lambda: {"success": True, "data": [{"year": 2026}]},
    )
    monkeypatch.setattr(
        "api.settings_api.SettingsAPI.get_settings",
        lambda: {"success": True, "data": {}},
    )

    controller.refresh_history()

    # refresh_history теперь только обновляет историю; статистика на главной не показывается.
    assert nav.app.main_view.years == [{"year": 2026}]


def test_report_tab_controller_refresh_reports(monkeypatch):
    nav = _DummyNav()
    controller = ReportTabController(nav)

    monkeypatch.setattr("api.salary_api.SalaryAPI.get_years", lambda: {"success": True, "data": [2026]})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_monthly_series_dto", lambda year=None: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_yearly_comparison_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_growth_rate_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_average_by_month_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_statistics", lambda year=None: {"success": True, "data": {}})
    monkeypatch.setattr(
        "api.settings_api.SettingsAPI.get_settings",
        lambda: {
            "success": True,
            "data": {"show_best_year_always": "1", "currency": "руб."},
        },
    )
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.get_best_periods",
        lambda: {"success": True, "data": {"best_month": None, "best_year": None}},
    )

    controller.refresh_reports()

    assert nav.app.report_view.years == [2026]
    assert len(nav.app.report_view.charts) == 4


def test_main_tab_controller_skips_rebuild_when_nothing_changed(monkeypatch):
    nav = _DummyNav()
    controller = MainTabController(nav)
    state = {
        "data": [{"year": 2025}, {"year": 2026}],
        "settings": {"history_layout_mode": "standard"},
    }

    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.get_all_grouped_by_year",
        lambda: {"success": True, "data": [dict(item) for item in state["data"]]},
    )
    monkeypatch.setattr(
        "api.settings_api.SettingsAPI.get_settings",
        lambda: {"success": True, "data": dict(state["settings"])},
    )

    controller.refresh_history()
    controller.refresh_history()
    assert nav.app.main_view.display_calls == 1

    # Новые данные (например, из бота) — карточки перестраиваются.
    state["data"].append({"year": 2027})
    controller.refresh_history()
    assert nav.app.main_view.display_calls == 2

    # Изменились настройки отображения — тоже перестраиваются.
    state["settings"] = {"history_layout_mode": "quarterly"}
    controller.refresh_history()
    assert nav.app.main_view.display_calls == 3


def _patch_current_year(monkeypatch, year):
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.get_current_period",
        lambda: {"success": True, "data": {"year": year, "month": 1}},
    )


def test_default_expanded_year_is_current_year(monkeypatch):
    _patch_current_year(monkeypatch, 2026)
    years = [{"year": 2024}, {"year": 2026}, {"year": 2025}]

    assert MainTabController._default_expanded_year(years) == 2026


def test_default_expanded_year_falls_back_to_latest_year(monkeypatch):
    # Январь 2027: данных за текущий год ещё нет — разворачиваем последний год с данными.
    _patch_current_year(monkeypatch, 2027)
    years = [{"year": 2024}, {"year": 2026}, {"year": 2025}]

    assert MainTabController._default_expanded_year(years) == 2026


def test_default_expanded_year_without_data(monkeypatch):
    _patch_current_year(monkeypatch, 2026)

    assert MainTabController._default_expanded_year([]) is None


def test_refresh_history_passes_default_expanded_year(monkeypatch):
    nav = _DummyNav()
    controller = MainTabController(nav)
    _patch_current_year(monkeypatch, 2026)
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.get_all_grouped_by_year",
        lambda: {"success": True, "data": [{"year": 2025}, {"year": 2026}]},
    )
    monkeypatch.setattr(
        "api.settings_api.SettingsAPI.get_settings",
        lambda: {"success": True, "data": {}},
    )

    controller.refresh_history()

    assert nav.app.main_view.default_expanded_year == 2026


def _patch_report_api(monkeypatch, monthly_calls):
    def fake_monthly(year=None):
        monthly_calls.append(year)
        return {"success": True, "data": {"items": [], "year": year}}

    monkeypatch.setattr("api.salary_api.SalaryAPI.get_years", lambda: {"success": True, "data": [2025, 2026]})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_monthly_series_dto", fake_monthly)
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_yearly_comparison_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_growth_rate_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_average_by_month_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_statistics", lambda year=None: {"success": True, "data": {}})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_salaries_by_year", lambda year: {"success": True, "data": []})
    monkeypatch.setattr(
        "api.settings_api.SettingsAPI.get_settings",
        lambda: {"success": True, "data": {"show_best_year_always": "1", "currency": "руб."}},
    )
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.get_best_periods",
        lambda: {"success": True, "data": {"best_month": None, "best_year": None}},
    )


def test_report_tab_controller_skips_redraw_when_nothing_changed(monkeypatch):
    nav = _DummyNav()
    controller = ReportTabController(nav)
    monthly_calls = []
    _patch_report_api(monkeypatch, monthly_calls)

    controller.refresh_reports()
    controller.refresh_reports()

    # Данные читаются каждый раз, а графики рисуются только один раз.
    assert len(monthly_calls) == 2
    assert len(nav.app.report_view.charts) == 4
    assert nav.app.report_view.kpi_args is not None


def test_report_tab_controller_redraws_when_year_changes(monkeypatch):
    nav = _DummyNav()
    controller = ReportTabController(nav)
    _patch_report_api(monkeypatch, [])

    controller.refresh_reports()
    nav.app.report_view.selected_year = 2025
    controller.on_year_selected(2025)

    assert len(nav.app.report_view.charts) == 8
    assert nav.app.report_view.kpi_args[1]["selected_year"] == 2025


def test_settings_tab_controller_save_settings(monkeypatch):
    nav = _DummyNav()
    controller = SettingsTabController(nav)
    saved = {}

    def fake_set_settings(settings):
        saved.update(settings)
        return {"success": True}

    monkeypatch.setattr("api.settings_api.SettingsAPI.set_settings", fake_set_settings)

    ok = controller.save_settings({"currency": "rub", "export_format": "csv"})

    assert ok is True
    assert saved == {"currency": "rub", "export_format": "csv"}


def test_main_tab_controller_create_auto_backup_on_close_enabled(monkeypatch):
    nav = _DummyNav()
    controller = MainTabController(nav)
    called = {"value": False}

    def fake_get_setting(key, default=None):
        if key == "backup_auto":
            value = "1"
        elif key == "backup_days":
            value = "7"
        else:
            value = default
        return {"success": True, "data": {"key": key, "value": value}}

    def fake_create_backup(comment=""):
        called["value"] = True
        assert comment == "auto_on_close"
        return {"success": True, "data": {"filepath": "db/backup/salary_backup_test.zip"}}

    monkeypatch.setattr("desktop.controllers.main_tab_controller.SettingsAPI.get_setting", fake_get_setting)
    monkeypatch.setattr("desktop.controllers.main_tab_controller.SalaryAPI.create_backup", fake_create_backup)

    ok = controller.create_auto_backup_on_close()

    assert ok is True
    assert called["value"] is True
