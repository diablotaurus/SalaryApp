import sys
import tkinter as tk

import pytest

from desktop.widgets.window_centering import (
    center_on_main_window,
    centered_position,
    install_native_dialog_centering,
)


def test_centered_position():
    assert centered_position((100, 50, 1000, 700), (400, 200)) == (400, 300)
    # Окно больше главного — всё равно по центру (координаты левее/выше главного)
    assert centered_position((100, 50, 300, 200), (500, 400)) == (0, -50)


def _show_main(root):
    root.geometry("1000x700+100+50")
    root.deiconify()
    root.update()


def _assert_centered(root, window):
    window.update()
    main_center = (root.winfo_x() + root.winfo_width() // 2, root.winfo_y() + root.winfo_height() // 2)
    center = (window.winfo_x() + window.winfo_width() // 2, window.winfo_y() + window.winfo_height() // 2)
    assert abs(center[0] - main_center[0]) <= 1 and abs(center[1] - main_center[1]) <= 1


def test_dialog_with_explicit_size_is_centered_on_main_window(root):
    _show_main(root)
    try:
        dialog = tk.Toplevel(root)
        tk.Label(dialog, text="Содержимое меньше заданного размера").pack()

        center_on_main_window(dialog, 400, 200)

        _assert_centered(root, dialog)
        assert (dialog.winfo_width(), dialog.winfo_height()) == (400, 200)
        assert dialog.winfo_ismapped()  # скрытие на время расчёта не оставляет окно скрытым
    finally:
        root.withdraw()


def test_nested_dialog_is_centered_on_main_window_not_on_parent(root):
    _show_main(root)
    try:
        parent = tk.Toplevel(root)
        parent.geometry("300x200+0+0")  # родитель в углу экрана
        parent.update()
        nested = tk.Toplevel(parent)
        tk.Label(nested, text="Вложенный диалог").pack(padx=40, pady=30)

        center_on_main_window(nested)

        _assert_centered(root, nested)
    finally:
        root.withdraw()


def test_withdrawn_window_stays_withdrawn(root):
    dialog = tk.Toplevel(root)
    dialog.withdraw()

    center_on_main_window(dialog, 300, 100)

    assert dialog.state() == "withdrawn"


@pytest.mark.skipif(sys.platform != "win32", reason="перехватчик только для Windows")
def test_native_dialog_hook_installs_and_is_removed_with_window(root):
    main = tk.Toplevel(root)
    main.update()

    assert install_native_dialog_centering(main) is True
    assert main._native_dialog_hook is not None

    main.destroy()
    assert main._native_dialog_hook is None
