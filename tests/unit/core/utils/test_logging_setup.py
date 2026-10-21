import logging
import logging.handlers
import sys

import pytest

from core.utils.logging_setup import configure_file_logging


@pytest.fixture
def isolated_root_logger():
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    yield root
    for handler in root.handlers:
        handler.close()
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def test_writes_log_to_file(isolated_root_logger, tmp_path):
    log_file = tmp_path / "web.log"

    configure_file_logging(str(log_file))
    logging.getLogger("web.test").warning("проверка записи в файл")

    for handler in isolated_root_logger.handlers:
        handler.flush()
    assert "проверка записи в файл" in log_file.read_text(encoding="utf-8")


def test_console_copy_only_when_console_exists(isolated_root_logger, tmp_path):
    configure_file_logging(str(tmp_path / "web.log"), console=True)

    stream_handlers = [
        h for h in isolated_root_logger.handlers
        if type(h) is logging.StreamHandler
    ]
    assert len(stream_handlers) == 1


def test_no_console_handler_under_pythonw(isolated_root_logger, tmp_path, monkeypatch):
    # У pythonw нет консоли: sys.stderr равен None
    monkeypatch.setattr(sys, "stderr", None)

    configure_file_logging(str(tmp_path / "web.log"), console=True)

    assert [type(h) for h in isolated_root_logger.handlers] == [
        logging.handlers.RotatingFileHandler
    ]


def test_log_time_is_moscow_with_label(isolated_root_logger, tmp_path):
    from core.utils.logging_setup import MoscowLogFormatter

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    record.created = 1792013923.5  # 2026-10-14 21:38:43.5 UTC
    record.msecs = 500

    assert MoscowLogFormatter("%(asctime)s").format(record) == "2026-10-15 00:38:43,500 МСК"


def test_file_log_uses_moscow_time(isolated_root_logger, tmp_path):
    log_file = tmp_path / "bot.log"

    configure_file_logging(str(log_file))
    logging.getLogger("bot.test").info("старт")

    for handler in isolated_root_logger.handlers:
        handler.flush()
    assert " МСК INFO старт" in log_file.read_text(encoding="utf-8")
