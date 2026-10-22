"""Bot routers."""

from bot.handlers.extras import router as extras_router
from bot.handlers.reports import router as reports_router
from bot.handlers.salary import router as salary_router

# Порядок подключения: отчёты и доп. выплаты — раньше ввода месяца (их кнопки
# работают посреди ввода); у роутера ввода последний обработчик — «устаревшая кнопка».
ROUTERS = (reports_router, extras_router, salary_router)

__all__ = ["ROUTERS", "extras_router", "reports_router", "salary_router"]
