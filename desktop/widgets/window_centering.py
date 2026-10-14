"""
Центрирование всех окон приложения по главному окну.

- Собственные диалоги (Toplevel) ставятся в центр главного окна, а не
  непосредственного родителя: вложенный диалог тоже оказывается по центру
  приложения, даже если главное окно не развёрнуто на весь экран.
- Стандартные окна Windows (messagebox, выбор цвета) Tk не позиционирует,
  и Windows ставила их где придётся. Перехватчик CBT (WH_CBT) двигает такой
  диалог в центр главного окна в момент его первого появления.
"""
from __future__ import annotations

import ctypes
import logging
import sys
import tkinter as tk
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Класс окна стандартных диалогов Windows (MessageBox, ChooseColor и т.п.)
NATIVE_DIALOG_CLASS = "#32770"


def centered_position(
    main_rect: Tuple[int, int, int, int], size: Tuple[int, int]
) -> Tuple[int, int]:
    """Левый верхний угол окна размера size по центру прямоугольника (x, y, ширина, высота)."""
    main_x, main_y, main_width, main_height = main_rect
    width, height = size
    return main_x + (main_width - width) // 2, main_y + (main_height - height) // 2


def center_on_main_window(
    window: tk.Toplevel, width: Optional[int] = None, height: Optional[int] = None
) -> None:
    """
    Поставить окно в центр главного окна приложения.

    Args:
        window: Окно (ещё не показанное или уже видимое)
        width, height: Размер окна, если он задаётся явно. Иначе берётся
            запрошенный содержимым размер: у ещё не показанного окна
            winfo_width() равен 1, и центрирование промахивалось.
    """
    main = window.nametowidget(".")  # корневое (главное) окно приложения
    main.update_idletasks()

    # Пока считается размер, ещё не показанное окно держим скрытым:
    # update_idletasks() иначе успевал показать его в позиции по умолчанию,
    # и заданная позиция то применялась, то нет (окно оказывалось в углу).
    hide_while_placing = not window.winfo_ismapped() and window.state() != "withdrawn"
    if hide_while_placing:
        window.withdraw()
    window.update_idletasks()

    size = (width or window.winfo_reqwidth(), height or window.winfo_reqheight())
    if main.winfo_ismapped() and main.winfo_width() > 1:
        main_rect = (main.winfo_x(), main.winfo_y(), main.winfo_width(), main.winfo_height())
    else:
        main_rect = (0, 0, main.winfo_screenwidth(), main.winfo_screenheight())

    x, y = centered_position(main_rect, size)
    explicit_size = f"{width}x{height}" if width and height else ""
    window.geometry(f"{explicit_size}+{x}+{y}")
    if hide_while_placing:
        window.deiconify()


def install_native_dialog_centering(main: tk.Tk) -> bool:
    """
    Центрировать стандартные окна Windows (messagebox, выбор цвета) по главному окну.

    Перехватчик ставится на поток интерфейса и живёт, пока живёт главное окно.

    Returns:
        bool: True, если перехватчик установлен (только Windows)
    """
    if sys.platform != "win32":
        return False
    try:
        return _install_cbt_hook(main)
    except (AttributeError, OSError):
        logger.exception("Не удалось установить центрирование стандартных окон")
        return False


def _install_cbt_hook(main: tk.Tk) -> bool:
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    wh_cbt, hcbt_destroywnd, hcbt_activate = 5, 4, 5
    swp_flags = 0x0001 | 0x0004 | 0x0010  # NOSIZE | NOZORDER | NOACTIVATE

    hook_proc_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    )
    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int, hook_proc_type, wintypes.HINSTANCE, wintypes.DWORD
    ]
    user32.SetWindowsHookExW.restype = wintypes.HHOOK
    user32.CallNextHookEx.argtypes = [
        wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    ]
    user32.CallNextHookEx.restype = ctypes.c_ssize_t
    user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]

    main_hwnd = int(main.wm_frame(), 16)
    # Уже отцентрированные диалоги: не возвращать окно на место, если пользователь
    # его подвинул и переключился. При закрытии дескриптор забывается — Windows
    # переиспользует дескрипторы окон.
    centered = set()

    def window_rect(hwnd):
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top

    def on_cbt_event(code, wparam, lparam):
        try:
            if code == hcbt_destroywnd:
                centered.discard(wparam)
            elif code == hcbt_activate and wparam not in centered:
                class_name = ctypes.create_unicode_buffer(32)
                user32.GetClassNameW(wparam, class_name, 32)
                if class_name.value == NATIVE_DIALOG_CLASS:
                    centered.add(wparam)
                    _x, _y, width, height = window_rect(wparam)
                    x, y = centered_position(window_rect(main_hwnd), (width, height))
                    user32.SetWindowPos(wparam, 0, x, y, 0, 0, swp_flags)
        except Exception:
            # Исключение в перехватчике Windows недопустимо: окно просто останется на месте
            pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    hook_proc = hook_proc_type(on_cbt_event)
    hook = user32.SetWindowsHookExW(wh_cbt, hook_proc, None, kernel32.GetCurrentThreadId())
    if not hook:
        return False

    # Ссылки нужны, пока перехватчик установлен: иначе сборщик мусора удалит обработчик
    main._native_dialog_hook = (hook, hook_proc)

    def uninstall(event):
        if event.widget is main and getattr(main, "_native_dialog_hook", None):
            user32.UnhookWindowsHookEx(main._native_dialog_hook[0])
            main._native_dialog_hook = None

    main.bind("<Destroy>", uninstall, add="+")
    return True
