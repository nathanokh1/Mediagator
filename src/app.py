"""
Mediagator — Application bootstrap.

Creates the QApplication, applies the dark theme, loads settings,
and launches the MainWindow.

Author: Nathan
"""

import logging
import sys

from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QIcon
from PyQt6.QtCore import Qt

_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"

# ---------------------------------------------------------------------------
# Light-theme QSS overrides (applied on top of shared button styles)
# ---------------------------------------------------------------------------
_LIGHT_QSS = """
QWidget          { background-color: #f0f0f5; color: #111111; }
QMainWindow      { background-color: #f0f0f5; }
QLabel           { color: #111111; }
QCheckBox        { color: #111111; }
QRadioButton     { color: #111111; }
QGroupBox        { border: 1px solid #bbb; border-radius: 6px;
                   margin-top: 12px; padding-top: 8px; color: #1a1a2e; }
QGroupBox::title { subcontrol-origin: margin; left: 10px;
                   padding: 0 4px; color: #e65100; }
QTreeWidget      { background-color: #ffffff;
                   alternate-background-color: #f5f5fa;
                   border: 1px solid #ccc; color: #1a1a2e; }
QHeaderView::section { background-color: #e0e0ea; border: none;
                        padding: 4px 8px; color: #444; }
QLineEdit, QListWidget, QTextBrowser {
    background-color: #ffffff; border: 1px solid #bbb;
    border-radius: 4px; color: #1a1a2e; }
QPushButton      { background-color: #e0e0ea; border: 1px solid #aaa;
                   border-radius: 4px; padding: 6px 14px; color: #1a1a2e; }
QPushButton:hover { background-color: #d0d0de; border-color: #888; }
QPushButton:disabled { color: #aaa; border-color: #ccc; background: #e8e8f0; }
QProgressBar     { background-color: #e0e0ea; border: 1px solid #bbb;
                   border-radius: 4px; color: #1a1a2e; }
QProgressBar::chunk { background-color: #ff9800; border-radius: 3px; }
QScrollBar:vertical   { background: #e0e0ea; width: 10px; }
QScrollBar::handle:vertical { background: #aaa; border-radius: 4px; }
QScrollBar:horizontal { background: #e0e0ea; height: 10px; }
QScrollBar::handle:horizontal { background: #aaa; border-radius: 4px; }
QWidget#navBar   { background: #e8e8f2; border-top: 1px solid #ccc; }
QWidget#appHeader { background: #fafafa; border-bottom: 3px solid #ff9800; }
QLabel#appTitle   { color: #e65100; }
QLabel#hintLabel    { color: #444; }
QLabel#sectionLabel { color: #111; }
QLabel#monoLabel    { color: #444; font-family: monospace; }
QRadioButton#hintRadio { color: #1a1a2e; }
QCheckBox#hintCheck { color: #444; }
QComboBox        { background: #ffffff; border: 1px solid #bbb;
                   border-radius: 4px; color: #1a1a2e; padding: 3px 8px; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background: #ffffff; color: #1a1a2e; }
QPushButton#primaryBtn:disabled {
    background: #c8c8d8; color: #888; border: 1px solid #bbb; }
QPushButton#secondaryBtn {
    background: transparent; color: #444; border: 1px solid #bbb; }
QPushButton#secondaryBtn:hover {
    background: #e0e0f0; color: #111; border-color: #888; }
QPushButton#secondaryBtn:pressed {
    background: #d0d0e0; }
QPushButton#accentBtn:disabled {
    background: #b0ccb2; color: #666; border: none; }
"""

from src.utils.logger import setup_logging, shutdown_logging
from src.config.settings import load_settings
from src.gui.wizard_state import WizardState
from src.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


# Extra QSS that applies on top of any base theme.
# Uses object names so rules are highly specific and never fight the base theme.
_SHARED_QSS = """
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffb74d, stop:1 #ff9800);
    color: #111;
    font-weight: bold;
    font-size: 13px;
    border: none;
    border-radius: 6px;
    padding: 0 24px;
    min-height: 40px;
    min-width: 120px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffe082, stop:1 #ffb74d);
}
QPushButton#primaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f57c00, stop:1 #e65100);
    color: #fff;
}
QPushButton#primaryBtn:disabled {
    background: #2a2a3e;
    color: #555;
    border: 1px solid #333;
}
QPushButton#secondaryBtn {
    background: transparent;
    color: #999;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 0 16px;
    min-height: 40px;
    min-width: 80px;
    font-size: 12px;
}
QPushButton#secondaryBtn:hover {
    background: #2a2a3e;
    color: #ddd;
    border-color: #888;
}
QPushButton#secondaryBtn:pressed {
    background: #333350;
    border-color: #aaa;
}
QPushButton#accentBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #66bb6a, stop:1 #388e3c);
    color: #fff;
    font-weight: bold;
    font-size: 14px;
    border: none;
    border-radius: 6px;
    padding: 0 28px;
    min-height: 44px;
    min-width: 160px;
}
QPushButton#accentBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #81c784, stop:1 #43a047);
}
QPushButton#accentBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2e7d32, stop:1 #1b5e20);
}
QPushButton#accentBtn:disabled {
    background: #2a2a3e;
    color: #555;
    border: 1px solid #333;
}
QWidget#navBar {
    background: #1e1e2e;
    border-top: 1px solid #333;
}
QWidget#appHeader {
    background: #1e1e2e;
    border-bottom: 1px solid #333;
}
QLabel#appTitle {
    color: #ff9800;
}
QLabel#hintLabel    { color: #888; }
QLabel#sectionLabel { color: #e0e0e0; }
QLabel#monoLabel    { color: #888; font-family: monospace; }
QRadioButton#hintRadio { color: #e0e0e0; }
QCheckBox#hintCheck { color: #888; }
"""


def _apply_dark_palette(app: QApplication) -> None:
    """Apply a custom dark QPalette to the application.

    Falls back gracefully if QDarkStyle is not available.

    Args:
        app: The running :class:`QApplication` instance.
    """
    try:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt6") + _SHARED_QSS)
        return
    except Exception:
        pass

    palette = QPalette()
    dark = QColor(30, 30, 46)
    mid_dark = QColor(40, 40, 58)
    text = QColor(224, 224, 224)
    highlight = QColor(255, 152, 0)
    disabled = QColor(100, 100, 120)

    palette.setColor(QPalette.ColorRole.Window, dark)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, mid_dark)
    palette.setColor(QPalette.ColorRole.AlternateBase, dark)
    palette.setColor(QPalette.ColorRole.ToolTipBase, dark)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, mid_dark)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 100, 100))
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)

    app.setPalette(palette)
    app.setStyleSheet(_SHARED_QSS + """
        QGroupBox {
            border: 1px solid #3a3a5a;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #ff9800;
        }
        QPushButton {
            background-color: #2e2e4e;
            border: 1px solid #4a4a6a;
            border-radius: 4px;
            padding: 6px 14px;
        }
        QPushButton:hover {
            background-color: #3e3e5e;
            border-color: #ff9800;
        }
        QPushButton:disabled {
            color: #555;
            border-color: #333;
        }
        QLineEdit, QListWidget, QTextBrowser {
            background-color: #242436;
            border: 1px solid #3a3a5a;
            border-radius: 4px;
            padding: 4px;
        }
        QProgressBar {
            background-color: #242436;
            border: 1px solid #3a3a5a;
            border-radius: 4px;
        }
        QProgressBar::chunk {
            background-color: #ff9800;
            border-radius: 3px;
        }
        QTreeWidget {
            background-color: #242436;
            alternate-background-color: #2a2a42;
            border: 1px solid #3a3a5a;
        }
        QHeaderView::section {
            background-color: #1e1e2e;
            border: none;
            padding: 4px 8px;
            color: #aaa;
        }
    """)


def apply_theme(app: QApplication, theme: str) -> None:
    """Switch the application-wide theme at runtime.

    Args:
        app: The running :class:`QApplication`.
        theme: ``"dark"`` or ``"light"``.
    """
    if theme == "light":
        # Reset to system default palette first, then apply light QSS
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet(_SHARED_QSS + _LIGHT_QSS)
    else:
        _apply_dark_palette(app)


def run() -> int:
    """Entry point — create QApplication and show MainWindow.

    Returns:
        Process exit code.
    """
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("Mediagator")
    app.setOrganizationName("Nathan")
    if _ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(_ICON_PATH)))

    settings = load_settings()

    # Apply saved theme before window is shown
    saved_theme = settings.get("theme", "dark")
    if saved_theme == "light":
        apply_theme(app, "light")
    else:
        _apply_dark_palette(app)

    state = WizardState(settings=settings)

    window = MainWindow(state, theme_applier=lambda t: apply_theme(app, t))
    window.show()

    exit_code = app.exec()
    shutdown_logging()
    return exit_code
