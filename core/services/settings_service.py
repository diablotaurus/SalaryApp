"""Business rules for application settings."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Dict, Mapping

from core.exceptions import ValidationError
from core.repositories.settings_repository import SettingsRepository


class SettingsService:
    """Validate and persist the supported application settings."""

    DEFAULTS: Dict[str, str] = {
        "currency": "руб.",
        "date_format": "%d.%m.%Y",
        "history_layout_mode": "standard",
        "main_stats_layout_mode": "row",
        "advance_color": "#0d6efd",
        "salary_color": "#198754",
        "total_color": "#dc3545",
        "month_title_font_size": "10",
        "month_total_font_size": "10",
        "month_data_font_size": "9",
        "show_best_year_always": "1",
        "backup_auto": "1",
        "backup_days": "30",
        "export_format": "csv",
    }

    _COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

    @classmethod
    def get_all_settings(cls) -> Dict[str, str]:
        settings = dict(cls.DEFAULTS)
        stored = SettingsRepository.get_all_settings()
        for key, value in stored.items():
            if key in cls.DEFAULTS:
                try:
                    settings[key] = cls._normalize(key, value)
                except ValidationError:
                    settings[key] = cls.DEFAULTS[key]
        return settings

    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        cls._require_supported_key(key)
        fallback = cls.DEFAULTS[key] if default is None else default
        value = SettingsRepository.get_setting(key, fallback)
        try:
            return cls._normalize(key, value)
        except ValidationError:
            return cls._normalize(key, fallback)

    @classmethod
    def set_setting(cls, key: str, value: Any) -> str:
        normalized = cls._normalize(key, value)
        SettingsRepository.set_setting(key, normalized)
        return normalized

    @classmethod
    def set_settings(cls, settings: Mapping[str, Any]) -> Dict[str, str]:
        normalized = {key: cls._normalize(key, value) for key, value in settings.items()}
        SettingsRepository.set_settings(normalized)
        return normalized

    @classmethod
    def delete_setting(cls, key: str) -> bool:
        cls._require_supported_key(key)
        return SettingsRepository.delete_setting(key)

    @classmethod
    def _normalize(cls, key: str, value: Any) -> str:
        cls._require_supported_key(key)
        validators: Dict[str, Callable[[Any], str]] = {
            "currency": cls._normalize_currency,
            "date_format": cls._normalize_date_format,
            "history_layout_mode": lambda raw: cls._normalize_choice(
                raw, {"standard", "quarterly"}, key
            ),
            "main_stats_layout_mode": lambda raw: cls._normalize_choice(
                raw, {"row", "column"}, key
            ),
            "advance_color": cls._normalize_color,
            "salary_color": cls._normalize_color,
            "total_color": cls._normalize_color,
            "month_title_font_size": lambda raw: cls._normalize_int(raw, 7, 18, key),
            "month_total_font_size": lambda raw: cls._normalize_int(raw, 7, 18, key),
            "month_data_font_size": lambda raw: cls._normalize_int(raw, 7, 18, key),
            "show_best_year_always": cls._normalize_bool,
            "backup_auto": cls._normalize_bool,
            "backup_days": lambda raw: cls._normalize_int(raw, 1, 365, key),
            "export_format": lambda raw: cls._normalize_choice(
                raw, {"csv", "json", "excel"}, key
            ),
        }
        return validators[key](value)

    @classmethod
    def _require_supported_key(cls, key: str) -> None:
        if key not in cls.DEFAULTS:
            raise ValidationError(f"Неизвестная настройка: {key}")

    @staticmethod
    def _normalize_currency(value: Any) -> str:
        normalized = str(value).strip()
        if not normalized or len(normalized) > 10:
            raise ValidationError("Обозначение валюты должно содержать от 1 до 10 символов")
        return normalized

    @staticmethod
    def _normalize_date_format(value: Any) -> str:
        normalized = str(value).strip()
        if not normalized or len(normalized) > 32:
            raise ValidationError("Некорректный формат даты")
        try:
            datetime(2026, 8, 27).strftime(normalized)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Некорректный формат даты") from exc
        return normalized

    @classmethod
    def _normalize_color(cls, value: Any) -> str:
        normalized = str(value).strip()
        if not cls._COLOR_PATTERN.fullmatch(normalized):
            raise ValidationError("Цвет должен быть указан в формате #RRGGBB")
        return normalized.lower()

    @staticmethod
    def _normalize_bool(value: Any) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return "1"
        if normalized in {"0", "false", "no", "n", "off"}:
            return "0"
        raise ValidationError("Ожидалось логическое значение")

    @staticmethod
    def _normalize_int(value: Any, minimum: int, maximum: int, key: str) -> str:
        try:
            normalized = int(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Настройка {key} должна быть целым числом") from exc
        if not minimum <= normalized <= maximum:
            raise ValidationError(
                f"Настройка {key} должна быть в диапазоне от {minimum} до {maximum}"
            )
        return str(normalized)

    @staticmethod
    def _normalize_choice(value: Any, allowed: set[str], key: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in allowed:
            choices = ", ".join(sorted(allowed))
            raise ValidationError(f"Настройка {key} должна иметь одно из значений: {choices}")
        return normalized
