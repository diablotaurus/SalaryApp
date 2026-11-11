"""
Загрузка matplotlib для вкладки аналитики.

Импорт тяжёлый (~0,8 с), поэтому при запуске приложения он не выполняется.
После показа окна библиотека подгружается в фоновом потоке, и к первому
открытию «Аналитики» она, как правило, уже готова.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional, Tuple

logger = logging.getLogger(__name__)

ChartBackend = Tuple[Any, Any]  # (FigureCanvasTkAgg, Figure)


def import_chart_backend() -> Optional[ChartBackend]:
    """
    Импортировать matplotlib с Tk-бэкендом.

    Returns:
        (FigureCanvasTkAgg, Figure) или None, если matplotlib не установлен.
    """
    try:
        import matplotlib
        matplotlib.use('TkAgg')  # Использование Tk-совместимого бэкенда
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
    except ImportError:
        return None
    return FigureCanvasTkAgg, Figure


class ChartBackendLoader:
    """
    Однократная загрузка графического бэкенда: заранее в фоне или по требованию.

    В фоновом потоке выполняется только импорт модулей — виджеты Tk там
    не создаются (Tk допускает работу с виджетами лишь из главного потока).
    """

    def __init__(self, importer: Callable[[], Optional[ChartBackend]] = import_chart_backend):
        self._importer = importer
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._loaded = False
        self._backend: Optional[ChartBackend] = None

    def start(self) -> None:
        """Начать загрузку в фоне (повторные вызовы ничего не делают)."""
        with self._lock:
            if self._loaded or self._thread is not None:
                return
            self._thread = threading.Thread(
                target=self._load_in_background, name="chart-backend-preload", daemon=True
            )
            self._thread.start()

    def get(self) -> Optional[ChartBackend]:
        """
        Вернуть бэкенд: дождаться фоновой загрузки или загрузить сейчас.

        Returns:
            (FigureCanvasTkAgg, Figure) или None, если matplotlib недоступен.
        """
        thread = self._thread
        if thread is not None:
            thread.join()
        with self._lock:
            if not self._loaded:
                self._backend = self._importer()
                self._loaded = True
            return self._backend

    def _load_in_background(self) -> None:
        try:
            backend = self._importer()
        except Exception:  # noqa: BLE001 - ошибка в фоне не должна пропасть бесследно
            logger.exception("Не удалось заранее загрузить matplotlib")
            return  # get() повторит импорт в главном потоке и покажет ошибку как обычно
        with self._lock:
            self._backend = backend
            self._loaded = True
