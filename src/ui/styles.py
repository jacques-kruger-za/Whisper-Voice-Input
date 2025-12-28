"""Qt stylesheets for the application."""

# Colors
COLOR_BG_DARK = "#0d1f2d"  # Dark teal blue (matches widget)
COLOR_BG_LIGHT = "#16213e"
COLOR_ACCENT = "#0f3460"
COLOR_HIGHLIGHT = "#00a8ff"  # Bright blue (was red)
COLOR_TEXT = "#eaeaea"
COLOR_TEXT_DIM = "#888888"
COLOR_SUCCESS = "#4ecca3"
COLOR_WARNING = "#ff9f1c"
COLOR_ERROR = "#e94560"

# Circular widget states (matched to _light PNG icons)
COLOR_WIDGET_IDLE = "#8fa3b8"        # Light grey-blue
COLOR_WIDGET_RECORDING = "#00bfff"   # Bright cyan-blue
COLOR_WIDGET_PROCESSING = "#ffcc00"  # Bright yellow-orange
COLOR_WIDGET_ERROR = "#ff4466"       # Bright coral-red

# Tray icon colors (darker for visibility on grey taskbars)
COLOR_TRAY_IDLE = "#4a5568"          # Darker grey (was #6b7b8c)
COLOR_TRAY_RECORDING = "#0077cc"     # Darker blue (was #00a8ff)
COLOR_TRAY_PROCESSING = "#cc8800"    # Darker amber (was #ffb347)
COLOR_TRAY_ERROR = "#cc3344"         # Darker red (was #e94560)

# Legacy (for backwards compatibility)
COLOR_IDLE = COLOR_WIDGET_IDLE
COLOR_RECORDING = COLOR_WIDGET_RECORDING
COLOR_PROCESSING = COLOR_WIDGET_PROCESSING

WIDGET_STYLE = f"""
QWidget#FloatingWidget {{
    background-color: {COLOR_BG_DARK};
    border: 2px solid {COLOR_ACCENT};
    border-radius: 10px;
}}

QLabel#StatusLabel {{
    color: {COLOR_TEXT};
    font-size: 12px;
    font-weight: bold;
}}

QLabel#StateLabel {{
    color: {COLOR_TEXT_DIM};
    font-size: 10px;
}}
"""

SETTINGS_STYLE = f"""
QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}}

QGroupBox {{
    border: 1px solid {COLOR_ACCENT};
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {COLOR_HIGHLIGHT};
}}

QPushButton {{
    background-color: {COLOR_ACCENT};
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    color: {COLOR_TEXT};
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {COLOR_HIGHLIGHT};
}}

QPushButton:pressed {{
    background-color: {COLOR_BG_LIGHT};
}}

QPushButton:disabled {{
    background-color: {COLOR_BG_LIGHT};
    color: {COLOR_TEXT_DIM};
}}

QLineEdit {{
    background-color: {COLOR_BG_LIGHT};
    border: 1px solid {COLOR_ACCENT};
    border-radius: 4px;
    padding: 6px;
    color: {COLOR_TEXT};
}}

QLineEdit:focus {{
    border-color: {COLOR_HIGHLIGHT};
}}

QComboBox {{
    background-color: {COLOR_BG_LIGHT};
    border: 1px solid {COLOR_ACCENT};
    border-radius: 4px;
    padding: 6px;
    color: {COLOR_TEXT};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {COLOR_TEXT};
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_LIGHT};
    border: 1px solid {COLOR_ACCENT};
    selection-background-color: {COLOR_HIGHLIGHT};
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 1px solid {COLOR_ACCENT};
    background-color: {COLOR_BG_LIGHT};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_HIGHLIGHT};
    border-color: {COLOR_HIGHLIGHT};
}}

QLabel {{
    color: {COLOR_TEXT};
}}

QLabel#SectionHeader {{
    font-size: 14px;
    font-weight: bold;
    color: {COLOR_HIGHLIGHT};
    padding: 5px 0;
}}

QScrollArea {{
    border: none;
}}

QScrollBar:vertical {{
    background-color: {COLOR_BG_LIGHT};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLOR_ACCENT};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""

TRAY_MENU_STYLE = f"""
QMenu {{
    background-color: {COLOR_BG_DARK};
    border: 1px solid {COLOR_ACCENT};
    border-radius: 4px;
    padding: 5px;
}}

QMenu::item {{
    padding: 8px 25px;
    color: {COLOR_TEXT};
}}

QMenu::item:selected {{
    background-color: {COLOR_HIGHLIGHT};
    border-radius: 3px;
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLOR_ACCENT};
    margin: 5px 10px;
}}
"""
