import tkinter as tk
from tkinter import ttk

from desktop.widgets.auto_hide_scrollbar import AutoHideScrollbar


def _scroll_area(root):
    root.geometry("400x300")
    frame = ttk.Frame(root)
    frame.pack(fill="both", expand=True)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(frame)
    scrollbar = AutoHideScrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    content = ttk.Frame(canvas, width=100, height=100)
    canvas.create_window((0, 0), window=content, anchor="nw")
    return canvas, scrollbar, content


def _set_content_height(root, canvas, content, height):
    content.configure(height=height)
    root.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))
    root.update_idletasks()


def test_hidden_when_content_fits(root):
    canvas, scrollbar, content = _scroll_area(root)

    _set_content_height(root, canvas, content, 100)

    assert scrollbar.grid_info() == {}


def test_shown_when_content_overflows_and_hidden_again(root):
    canvas, scrollbar, content = _scroll_area(root)

    _set_content_height(root, canvas, content, 2000)
    assert scrollbar.grid_info()["column"] == 1  # вернулась на своё место

    _set_content_height(root, canvas, content, 100)
    assert scrollbar.grid_info() == {}
