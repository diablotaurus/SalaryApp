import logging

from desktop.app import App


def test_callback_error_is_logged_and_shown(monkeypatch, caplog):
    # Раньше ошибка в обработчике кнопки печаталась в консоль, которой у pythonw нет.
    shown = {}
    monkeypatch.setattr(
        "desktop.app.messagebox.showerror",
        lambda title, message: shown.update(title=title, message=message),
    )
    error = ValueError("boom")

    with caplog.at_level(logging.ERROR):
        App.report_callback_exception(None, ValueError, error, error.__traceback__)

    assert any(record.exc_info and record.exc_info[1] is error for record in caplog.records)
    assert "boom" in shown["message"]
    assert "журнал" in shown["message"]
