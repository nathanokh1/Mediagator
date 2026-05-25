"""
MediaMitigator — Application bootstrap.

Creates the QApplication, applies the dark theme, loads settings,
and launches the MainWindow.

Author: Nathan
"""

import logging
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

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


def run() -> int:
    """Entry point — create QApplication and show MainWindow.

    Returns:
        Process exit code.
    """
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("MediaMitigator")
    app.setOrganizationName("Nathan")

    _apply_dark_palette(app)

    settings = load_settings()
    state = WizardState(settings=settings)

    window = MainWindow(state)
    window.show()

    exit_code = app.exec()
    shutdown_logging()
    return exit_code
