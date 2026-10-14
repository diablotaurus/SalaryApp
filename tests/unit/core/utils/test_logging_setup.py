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
