"""Presentation constants for report charts and their tooltips."""

# Поля графика — доли размера фигуры
CHART_MARGIN_LEFT = 0.06
CHART_MARGIN_RIGHT = 0.98
CHART_MARGIN_TOP = 0.90
CHART_MARGIN_BOTTOM = 0.12
# Левое поле не уже этого: иначе в нешироком окне подпись оси Y уходит за край.
# В дюймах, потому что шрифты графика тоже растут с масштабом экрана (DPI).
CHART_MIN_LEFT_INCH = 1.0

TOOLTIP_FONT_SIZE = 10
TOOLTIP_OFFSET_PX = 12
TOOLTIP_MARGIN_PX = 6
TOOLTIP_ZORDER = 20
TOOLTIP_BACKGROUND = "#ffffff"
TOOLTIP_BORDER = "#9ca3af"
TOOLTIP_TEXT_COLOR = "#202124"
TOOLTIP_BORDER_WIDTH = 0.8
TOOLTIP_BOX_STYLE = "round,pad=0.5,rounding_size=0.2"
