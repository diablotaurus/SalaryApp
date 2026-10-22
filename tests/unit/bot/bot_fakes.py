"""Подставные объекты aiogram для тестов кнопок бота (без сети)."""
import asyncio
from datetime import datetime as _dt

from aiogram.types import CallbackQuery, Chat, Message, User

from bot.handlers import ROUTERS


class FakeMessage:
    def __init__(self, text="", edit_error=None):
        self.text = text
        self.answers = []
        self.edited = []
        self._edit_error = edit_error

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

    async def answer_photo(self, photo, **kwargs):
        self.answers.append(("photo", {"file": photo, **kwargs}))

    async def answer_document(self, document, **kwargs):
        self.answers.append(("document", {"file": document, **kwargs}))

    async def edit_text(self, text, **kwargs):
        if self._edit_error:
            raise self._edit_error
        self.edited.append(text)


class FakeCallback:
    def __init__(self, data, message=None):
        self.data = data
        self.message = message or FakeMessage("За какой месяц вносим данные?")
        self.answered = []

    async def answer(self, text=None, **kwargs):
        self.answered.append(text)


class FakeState:
    def __init__(self, data=None, current_state=None):
        self.data = data or {}
        self.current_state = current_state
        self.cleared = False

    async def set_state(self, state):
        self.current_state = state

    async def get_state(self):
        return self.current_state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.cleared = True
        self.current_state = None


def buttons(markup):
    return [(button.text, button.callback_data) for row in markup.inline_keyboard for button in row]


def route_callback(data, state=None):
    callback = CallbackQuery(
        id="1",
        from_user=User(id=1, is_bot=False, first_name="u"),
        chat_instance="c",
        data=data,
    )

    async def _find():
        # Порядок роутеров — как в bot/main.py
        for router in ROUTERS:
            for handler in router.callback_query.handlers:
                matched, _ = await handler.check(callback, raw_state=state.state if state else None, bot=None)
                if matched:
                    return handler.callback
        return None

    return asyncio.run(_find())


def _month(month, total=0.0, name=None):
    return {
        "month": month, "month_name": name or f"М{month}", "has_data": total > 0,
        "advance": total / 3, "salary": total * 2 / 3, "total": total,
        "advance_date": f"28.{month:02}.2026" if total else "", "salary_date": "",
    }


def _year(year, totals, average):
    months = [_month(m, totals.get(m, 0.0)) for m in range(1, 13)]
    return {
        "year": year,
        "summary": {
            "total": sum(totals.values()), "average_monthly": average,
            "months_with_data": len(totals),
        },
        "months": months,
    }


# Три года для отчётов: 2026 неполный, 2025 полный, 2024 пропущен
SAMPLE_YEARS = [
    _year(2026, {1: 100000.0, 2: 110000.0, 9: 120000.0, 10: 15000.0}, 110000.0),
    _year(2025, {m: 100000.0 for m in range(1, 13)}, 100000.0),
    _year(2023, {5: 50000.0}, 50000.0),
]


def route_message(text, state=None):
    """Обработчик сообщения в порядке роутеров bot/main.py (настоящие фильтры aiogram)."""
    message = Message(
        message_id=1, date=_dt.now(), chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="u"), text=text,
    )

    async def _find():
        for router in ROUTERS:
            for handler in router.message.handlers:
                matched, _ = await handler.check(message, raw_state=state.state if state else None, bot=None)
                if matched:
                    return handler.callback
        return None

    return asyncio.run(_find())
