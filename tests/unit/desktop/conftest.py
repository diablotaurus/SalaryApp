import tkinter as tk

import pytest


@pytest.fixture(scope="session")
def tk_root():
    # Одно окно на весь прогон: многократное создание Tk() подряд на Windows
    # нестабильно (повторный Tk() иногда падает с TclError, и тесты пропускались).
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk недоступен (нет графической среды)")
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def root(tk_root):
    yield tk_root
    for child in tk_root.winfo_children():
        child.destroy()
