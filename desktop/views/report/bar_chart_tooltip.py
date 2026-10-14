"""Hover annotations for bars, independent of salary data and calculations."""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from .chart_constants import (
    TOOLTIP_BACKGROUND,
    TOOLTIP_BORDER,
    TOOLTIP_BORDER_WIDTH,
    TOOLTIP_BOX_STYLE,
    TOOLTIP_FONT_SIZE,
    TOOLTIP_MARGIN_PX,
    TOOLTIP_OFFSET_PX,
    TOOLTIP_TEXT_COLOR,
    TOOLTIP_ZORDER,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import FigureCanvasBase, MouseEvent
    from matplotlib.patches import Rectangle


class BarChartTooltip:
    """Bind already formatted text to bars on one chart canvas."""

    def __init__(self, axes: Axes, canvas: FigureCanvasBase, widget=None):
        self._axes = axes
        self._canvas = canvas
        self._items: tuple[tuple[Rectangle, str], ...] = ()
        self._annotation = None
        self._active_bar = None
        self._cursor = None
        self._widget = widget
        self._bindings = {}
        self._connections = [
            canvas.mpl_connect("motion_notify_event", self._on_motion),
            canvas.mpl_connect("axes_leave_event", self._hide),
            canvas.mpl_connect("figure_leave_event", self._hide),
            canvas.mpl_connect("resize_event", self._hide),
            canvas.mpl_connect("close_event", self.disconnect),
        ]
        if widget is not None:
            self._bindings = {
                "<Destroy>": widget.bind("<Destroy>", self.disconnect, add="+"),
                "<Unmap>": widget.bind("<Unmap>", self._hide, add="+"),
            }

    def set_items(self, items: Iterable[tuple[Rectangle, str]]) -> None:
        """Replace bar bindings after the axes have been rebuilt."""
        self.clear()
        if not self._connections:
            return
        self._items = tuple(items)
        if not self._items:
            return
        self._annotation = self._axes.annotate(
            "",
            xy=(0, 0),
            xycoords="figure pixels",
            xytext=(0, 0),
            textcoords="figure pixels",
            ha="left",
            va="bottom",
            fontsize=TOOLTIP_FONT_SIZE,
            color=TOOLTIP_TEXT_COLOR,
            bbox={
                "boxstyle": TOOLTIP_BOX_STYLE,
                "facecolor": TOOLTIP_BACKGROUND,
                "edgecolor": TOOLTIP_BORDER,
                "linewidth": TOOLTIP_BORDER_WIDTH,
            },
            zorder=TOOLTIP_ZORDER,
            annotation_clip=False,
            visible=False,
        )
        self._annotation.set_in_layout(False)

    def clear(self) -> None:
        """Drop old artists before a chart redraw, without scheduling a draw."""
        if self._annotation is not None:
            if self._annotation in self._axes.texts:
                self._annotation.remove()
            self._annotation = None
        self._items = ()
        self._active_bar = None
        self._cursor = None

    def disconnect(self, _event=None) -> None:
        """Release callbacks on canvas destruction; safe to call twice."""
        for connection in self._connections:
            self._canvas.mpl_disconnect(connection)
        self._connections.clear()
        if self._bindings and self._widget.winfo_exists():
            for sequence, binding in self._bindings.items():
                self._widget.unbind(sequence, binding)
        self._bindings.clear()
        self._widget = None
        self.clear()

    def _on_motion(self, event: MouseEvent) -> None:
        if event.inaxes is not self._axes or self._annotation is None:
            self._hide()
            return

        for bar, text in reversed(self._items):
            if bar.axes is not self._axes or not bar.get_visible():
                continue
            if bar.contains(event)[0]:
                cursor = (event.x, event.y)
                if self._active_bar is bar and self._cursor == cursor:
                    return
                self._active_bar = bar
                self._cursor = cursor
                self._annotation.set_text(text)
                self._annotation.set_visible(True)
                self._position(event)
                self._canvas.draw_idle()
                return
        self._hide()

    def _hide(self, _event=None) -> None:
        self._active_bar = None
        self._cursor = None
        if self._annotation is not None and self._annotation.get_visible():
            self._annotation.set_visible(False)
            self._canvas.draw_idle()

    def _position(self, event: MouseEvent) -> None:
        """Flip at the cursor, then clamp the full text box to the canvas."""
        annotation = self._annotation
        renderer = self._canvas.get_renderer()
        bounds = self._axes.figure.bbox.padded(-TOOLTIP_MARGIN_PX)
        x = event.x + TOOLTIP_OFFSET_PX
        y = event.y + TOOLTIP_OFFSET_PX
        annotation.set_position((x, y))
        annotation.update_positions(renderer)
        annotation.update_bbox_position_size(renderer)
        box = annotation.get_bbox_patch().get_window_extent(renderer)

        # Include the border padding, not just the text's dimensions.
        left_padding = x - box.x0
        bottom_padding = y - box.y0
        left = box.x0
        bottom = box.y0
        if box.x1 > bounds.x1:
            left = event.x - TOOLTIP_OFFSET_PX - box.width
        if box.y1 > bounds.y1:
            bottom = event.y - TOOLTIP_OFFSET_PX - box.height
        left = max(bounds.x0, min(left, bounds.x1 - box.width))
        bottom = max(bounds.y0, min(bottom, bounds.y1 - box.height))
        annotation.set_position((left + left_padding, bottom + bottom_padding))
