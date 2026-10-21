"""Bot routers."""

from bot.handlers.reports import router as reports_router
from bot.handlers.salary import router as salary_router

__all__ = ["reports_router", "salary_router"]
