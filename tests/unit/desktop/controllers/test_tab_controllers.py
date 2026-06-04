from desktop.controllers.main_tab_controller import MainTabController
from desktop.controllers.report_tab_controller import ReportTabController
from desktop.controllers.settings_tab_controller import SettingsTabController


class _DummyView:
    def __init__(self):
        self.years = None
        self.settings = None
        self.charts = []
        self.kpi_args = None

    def display_years(self, data):
        self.years = data

    def update_statistics(self, data):
        self.stats = data

    def update_years_list(self, years):
        self.years = years

    def get_selected_year(self):
        return None

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
        "api.salary_api.SalaryAPI.get_statistics",
        lambda year=None: {"success": True, "data": {"total": 1}},
    )

    controller.refresh_history()

    assert nav.app.main_view.years == [{"year": 2026}]
    assert nav.app.main_view.stats == {"total": 1}


def test_report_tab_controller_refresh_reports(monkeypatch):
    nav = _DummyNav()
    controller = ReportTabController(nav)

    monkeypatch.setattr("api.salary_api.SalaryAPI.get_years", lambda: {"success": True, "data": [2026]})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_monthly_series_dto", lambda year=None: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_yearly_comparison_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_growth_rate_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_average_by_month_dto", lambda: {"success": True, "data": []})
    monkeypatch.setattr("api.salary_api.SalaryAPI.get_statistics", lambda year=None: {"success": True, "data": {}})
    monkeypatch.setattr("api.settings_api.SettingsAPI.get_setting", lambda key, default=None: {"success": True, "data": {"value": True}})
    monkeypatch.setattr(
        "api.salary_api.SalaryAPI.get_best_periods",
        lambda: {"success": True, "data": {"best_month": None, "best_year": None}},
    )

    controller.refresh_reports()

    assert nav.app.report_view.years == [2026]
    assert len(nav.app.report_view.charts) == 4


def test_settings_tab_controller_save_settings(monkeypatch):
    nav = _DummyNav()
    controller = SettingsTabController(nav)
    saved = {}

    def fake_set_setting(key, value):
        saved[key] = value
        return {"success": True}

    monkeypatch.setattr("api.settings_api.SettingsAPI.set_setting", fake_set_setting)

    ok = controller.save_settings({"currency": "rub", "theme": "clam"})

    assert ok is True
    assert saved == {"currency": "rub", "theme": "clam"}


def test_main_tab_controller_create_auto_backup_on_close_enabled(monkeypatch):
    nav = _DummyNav()
    controller = MainTabController(nav)
    called = {"value": False}

    def fake_get_setting(key, default=None):
        if key == "backup_auto":
            return "1"
        if key == "backup_days":
            return "7"
        return default

    def fake_create_backup(comment=""):
        called["value"] = True
        assert comment == "auto_on_close"
        return "db/backup/salary_backup_test.zip"

    monkeypatch.setattr("desktop.controllers.main_tab_controller.SettingsRepository.get_setting", fake_get_setting)
    monkeypatch.setattr("desktop.controllers.main_tab_controller.BackupService.create_backup", fake_create_backup)

    ok = controller.create_auto_backup_on_close()

    assert ok is True
    assert called["value"] is True
