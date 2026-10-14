"""
Кэш последней отрисовки вкладки.

Позволяет контроллеру пропустить перестройку интерфейса, если данные для неё
не изменились с прошлого раза. Сами данные при этом каждый раз читаются заново
(это дёшево), поэтому изменения из бота или веба по-прежнему подхватываются.
"""
from __future__ import annotations

import copy
from typing import Any


class RenderCache:
    """Помнит входные данные последней успешной отрисовки."""

    def __init__(self):
        self._snapshot: Any = None
        self._has_snapshot = False

    def is_current(self, value: Any) -> bool:
        """True, если value совпадает с уже отрисованными данными."""
        return self._has_snapshot and self._snapshot == value

    def remember(self, value: Any) -> None:
        """Запомнить данные после успешной отрисовки (копия защищает от мутаций)."""
        self._snapshot = copy.deepcopy(value)
        self._has_snapshot = True

    def invalidate(self) -> None:
        """Сбросить кэш: следующая отрисовка выполнится обязательно."""
        self._snapshot = None
        self._has_snapshot = False
