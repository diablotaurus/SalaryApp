"""
Application-level typed exceptions.
"""
from __future__ import annotations


class SalaryAppError(Exception):
    """Base application error with a safe message for UI/API responses."""

    def __init__(self, message: str, *, user_message: str | None = None):
        super().__init__(message)
        self.user_message = user_message or message


class ValidationError(SalaryAppError):
    """Input data validation failed."""


class DataAccessError(SalaryAppError):
    """Database or storage access failed."""


class ServiceError(SalaryAppError):
    """Business/service level operation failed."""


class ExportError(SalaryAppError):
    """Export operation failed."""


class BackupError(SalaryAppError):
    """Backup/restore operation failed."""


class PresentationError(SalaryAppError):
    """Desktop/web presentation layer operation failed."""


RECOVERABLE_EXCEPTIONS = (ValueError, TypeError, KeyError, RuntimeError, OSError)


def to_app_error(exc: Exception, default_message: str) -> SalaryAppError:
    """Map built-in exceptions to typed application errors."""
    if isinstance(exc, SalaryAppError):
        return exc
    if isinstance(exc, (ValueError, TypeError)):
        return ValidationError(str(exc), user_message=str(exc))
    if isinstance(exc, (OSError, RuntimeError)):
        return ServiceError(str(exc), user_message=default_message)
    if isinstance(exc, KeyError):
        return ServiceError(str(exc), user_message=default_message)
    return ServiceError(str(exc), user_message=default_message)
