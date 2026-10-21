"""Подставные объекты aiogram для тестов кнопок бота (без сети)."""
import asyncio

from aiogram.types import CallbackQuery, User

from bot.handlers.salary import router


class FakeMessage:
    def __init__(self, text="", edit_error=None):
        self.text = text
        self.answers = []
        self.edited = []
        self._edit_error = edit_error

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

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
        for handler in router.callback_query.handlers:
            matched, _ = await handler.check(callback, raw_state=state.state if state else None, bot=None)
            if matched:
                return handler.callback
        return None

    return asyncio.run(_find())
