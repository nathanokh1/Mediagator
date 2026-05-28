"""
Mediagator — MainWindow.

Hosts the chevron step indicator and the QStackedWidget that
renders each of the 8 wizard steps.

Author: Nathan
"""

import logging
import webbrowser
from pathlib import Path
from typing import Callable
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStackedWidget, QFrame, QPushButton,
)
from PyQt6.QtCore import Qt, QRect, QPointF, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient, QPen, QPolygonF, QPixmap, QIcon
from src.gui.update_dialog import UpdateDialog

_ICON_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "icon_512.png"

from src.config.constants import (
    WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, STEP_NAMES,
    APP_VERSION, GITHUB_RELEASES_URL,
)
from src.config.settings import save_settings
from src.gui.wizard_state import WizardState
from src.gui.steps.step_00_welcome import WelcomeStep
from src.gui.steps.step_01_drive_selection import DriveSelectionStep
from src.gui.steps.step_02_initial_scan import InitialScanStep
from src.gui.steps.step_03_destination import DestinationStep
from src.gui.steps.step_04_folder_review import FolderReviewStep
from src.gui.steps.step_05_transfer_settings import TransferSettingsStep
from src.gui.steps.step_06_pre_transfer import PreTransferStep
from src.gui.steps.step_07_progress import TransferProgressStep
from src.gui.steps.step_08_report import ReportStep

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Application main window containing the 8-step wizard.

    Args:
        state: Shared :class:`WizardState` instance.
    """

    def __init__(
        self,
        state: WizardState,
        theme_applier: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the main window.

        Args:
            state: Shared wizard state passed to every step.
            theme_applier: Optional callback ``fn(theme_name)`` that switches
                the application palette.  If omitted, theme toggle is a no-op.
        """
        super().__init__(parent)
        self._state = state
        self._theme_applier = theme_applier or (lambda _: None)
        self._current_step = 0
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1200, 800)
        self._build_ui()
        self._start_update_check()

    def _build_ui(self) -> None:
        """Construct the main window layout."""
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        self._is_dark = self._state.settings.get("theme", "dark") == "dark"
        header = QFrame()
        header.setObjectName("appHeader")
        header.setFixedHeight(56)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(10)

        # App icon + title as a tightly grouped pair
        brand_widget = QWidget()
        brand_widget.setStyleSheet("background: transparent;")
        brand_row = QHBoxLayout(brand_widget)
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(8)

        if _ICON_PATH.exists():
            icon_lbl = QLabel()
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            px = QPixmap(str(_ICON_PATH)).scaled(
                32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_lbl.setPixmap(px)
            icon_lbl.setFixedSize(32, 32)
            brand_row.addWidget(icon_lbl)

        app_title = QLabel("Mediagator")
        app_title.setObjectName("appTitle")
        app_title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        app_title.setFont(font)
        brand_row.addWidget(app_title)

        # Version label
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setObjectName("versionLabel")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        ver_lbl.setStyleSheet("color: #888; font-size: 11px; padding-left: 4px;")
        brand_row.addWidget(ver_lbl)

        header_layout.addWidget(brand_widget)
        header_layout.addStretch()

        # Update-available button (hidden until checker fires)
        self._update_btn = QPushButton("⬆ Update available")
        self._update_btn.setObjectName("updateBtn")
        self._update_btn.setFixedHeight(26)
        self._update_btn.setStyleSheet(
            "QPushButton { background: #ff9800; color: #000; border-radius: 4px; "
            "font-size: 11px; padding: 0 10px; font-weight: bold; }"
            "QPushButton:hover { background: #ffb74d; }"
        )
        self._update_btn.setToolTip("A new version of Mediagator is available — click to download")
        self._update_btn.clicked.connect(lambda: webbrowser.open(GITHUB_RELEASES_URL))
        self._update_btn.hide()
        header_layout.addWidget(self._update_btn)

        # Theme toggle — flat pill button, no emoji circle
        current_theme = self._state.settings.get("theme", "dark")
        self._theme_btn = QPushButton("☀  Light" if current_theme == "dark" else "🌙  Dark")
        self._theme_btn.setToolTip("Switch to light theme" if current_theme == "dark" else "Switch to dark theme")
        self._theme_btn.setFixedHeight(30)
        self._update_theme_btn(self._is_dark)
        self._theme_btn.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self._theme_btn)

        root.addWidget(header)

        # Chevron step indicator
        self._breadcrumb = _ChevronStepper(STEP_NAMES)
        root.addWidget(self._breadcrumb)

        # Stacked widget
        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        # Build steps
        self._steps: list[QWidget] = []
        self._step_classes = [
            WelcomeStep,
            DriveSelectionStep,
            InitialScanStep,
            DestinationStep,
            FolderReviewStep,
            TransferSettingsStep,
            PreTransferStep,
            TransferProgressStep,
            ReportStep,
        ]

        for StepClass in self._step_classes:
            step = StepClass(self._state)
            self._steps.append(step)
            self._stack.addWidget(step)

        # Wire navigation signals
        self._connect_signals()

        # Skip welcome if user has opted out
        start = 1 if self._state.settings.get("welcome_seen", False) else 0
        self._go_to_step(start)

    def _connect_signals(self) -> None:
        """Connect next_requested / back_requested signals for each step."""
        for i, step in enumerate(self._steps):
            if hasattr(step, "next_requested"):
                step.next_requested.connect(lambda idx=i: self._go_to_step(idx + 1))
            if hasattr(step, "back_requested"):
                step.back_requested.connect(lambda idx=i: self._go_to_step(idx - 1))

        # Step 9 (Report): "Start New Transfer" → back to Drive Selection (step 1)
        report_step = self._steps[8]
        if hasattr(report_step, "new_transfer_requested"):
            report_step.new_transfer_requested.connect(lambda: self._go_to_step(1))

    def _update_theme_btn(self, is_dark: bool) -> None:
        """Apply the correct inline style to the theme toggle button."""
        if is_dark:
            self._theme_btn.setStyleSheet(
                "QPushButton { background: #2a2a3e; border: 1px solid #555;"
                " border-radius: 6px; font-size: 11px; color: #bbb; padding: 0 12px; }"
                "QPushButton:hover { background: #3a3a52; border-color: #ff9800; color: #fff; }"
            )
        else:
            self._theme_btn.setStyleSheet(
                "QPushButton { background: #f0f0f8; border: 1px solid #ccc;"
                " border-radius: 6px; font-size: 11px; color: #444; padding: 0 12px; }"
                "QPushButton:hover { background: #e4e4f0; border-color: #ff9800; color: #111; }"
            )

    def _toggle_theme(self) -> None:
        """Switch between dark and light themes and persist the choice."""
        current = self._state.settings.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self._state.settings["theme"] = new_theme
        save_settings(self._state.settings)

        self._theme_applier(new_theme)

        is_dark = new_theme == "dark"
        self._is_dark = is_dark
        self._theme_btn.setText("☀  Light" if is_dark else "🌙  Dark")
        self._theme_btn.setToolTip(
            "Switch to light theme" if is_dark else "Switch to dark theme"
        )
        self._update_theme_btn(is_dark)
        self._breadcrumb.apply_theme(is_dark)
        logger.info("Theme switched to: %s", new_theme)

    def _go_to_step(self, index: int) -> None:
        """Navigate to a wizard step by index.

        Args:
            index: 0-based step index.
        """
        if index < 0 or index >= len(self._steps):
            return
        self._current_step = index
        self._stack.setCurrentIndex(index)
        self._breadcrumb.set_active(index)

        step = self._steps[index]
        if hasattr(step, "refresh"):
            step.refresh()

    def _start_update_check(self) -> None:
        """Spawn a background thread to check GitHub for a newer release."""
        self._update_checker = _UpdateChecker(APP_VERSION)
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.start()

    def _on_update_available(self, latest: str, download_url: str) -> None:
        """Show the update button (and store download URL) when newer version found."""
        self._pending_update_url = download_url
        self._update_btn.setText(f"⬆  v{latest} available")
        self._update_btn.setToolTip(
            f"Mediagator v{latest} is available — click to update"
        )
        # Disconnect the old "open releases page" handler and wire update dialog
        try:
            self._update_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self._update_btn.clicked.connect(
            lambda: self._show_update_dialog(latest, download_url)
        )
        self._update_btn.show()
        logger.info("Update available: v%s (running v%s)", latest, APP_VERSION)

    def _show_update_dialog(self, version: str, download_url: str) -> None:
        """Open the update dialog."""
        dlg = UpdateDialog(version, download_url, self)
        dlg.exec()


class _UpdateChecker(QThread):
    """Background thread that checks GitHub for a newer release.

    Emits ``update_available(version, download_url)`` when a newer release
    exists and has a matching ``.exe`` installer asset.  Runs once on startup
    and silently swallows all network/parse errors.
    """

    update_available = pyqtSignal(str, str)  # (version, download_url)

    def __init__(self, current_version: str, parent=None) -> None:
        super().__init__(parent)
        self._current = current_version
        self.daemon = True

    def run(self) -> None:
        try:
            import urllib.request
            import json
            from src.config.constants import GITHUB_LATEST_API, GITHUB_RELEASES_URL

            req = urllib.request.Request(
                GITHUB_LATEST_API,
                headers={"User-Agent": "Mediagator-update-check"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            tag = data.get("tag_name", "").lstrip("v")
            if not tag or not self._is_newer(tag):
                return

            # Look for an installer asset (.exe) in the release assets
            download_url = ""
            for asset in data.get("assets", []):
                name: str = asset.get("name", "")
                if name.lower().endswith(".exe") and "setup" in name.lower():
                    download_url = asset.get("browser_download_url", "")
                    break

            # Fall back to the releases page URL if no asset found yet
            if not download_url:
                download_url = GITHUB_RELEASES_URL

            self.update_available.emit(tag, download_url)
        except Exception:
            pass  # network unavailable, behind proxy, rate-limited — all fine

    @staticmethod
    def _is_newer(tag: str) -> bool:
        """Return True if *tag* is a higher semver than the running version."""
        from src.config.constants import APP_VERSION
        try:
            def _parts(v: str) -> tuple[int, ...]:
                return tuple(int(x) for x in v.split("."))
            return _parts(tag) > _parts(APP_VERSION)
        except ValueError:
            return False


class _ChevronStepper(QWidget):
    """Chevron-style step indicator painted directly with QPainter.

    Each step is a coloured arrow/chevron shape:
      • Future   – dark slate (#1e1e30), dim text
      • Completed – green gradient, white text
      • Active    – orange gradient, bold black text
    """

    _H          = 46        # total widget height in pixels
    _ARROW      = 18        # horizontal depth of the chevron point
    _V_PAD      = 5         # vertical inset for the colour fill (gap at top/bottom)
    _RADIUS     = 3         # corner radius on first/last step

    # Short labels that fit comfortably inside a chevron
    _SHORT = [
        "Welcome", "Drive Select", "Scan", "Destination",
        "Review", "Settings", "Analysis", "Transfer", "Report",
    ]

    # Gradient colour pairs (top, bottom) for each state
    _GRAD_ACTIVE    = ("#ffb74d", "#f57c00")
    _GRAD_DONE      = ("#66bb6a", "#388e3c")
    _GRAD_FUTURE    = ("#252538", "#1a1a2e")

    def __init__(self, names: list[str], parent=None) -> None:
        super().__init__(parent)
        self._n       = len(names)
        self._names   = self._SHORT[: self._n]
        self._active  = 0
        self._is_dark = True
        self.setFixedHeight(self._H)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def set_active(self, index: int) -> None:
        self._active = index
        self.update()

    def apply_theme(self, is_dark: bool) -> None:
        """Update chevron colours when the application theme changes."""
        self._is_dark = is_dark
        if is_dark:
            self._GRAD_FUTURE = ("#252538", "#1a1a2e")
        else:
            self._GRAD_FUTURE = ("#d4d4e4", "#bdbdcd")
        self.update()

    # ------------------------------------------------------------------

    def _chevron_poly(self, i: int, x: float, w: float, h: float) -> QPolygonF:
        """Return the QPolygonF for chevron i."""
        top    = float(self._V_PAD)
        bot    = float(h - self._V_PAD)
        mid    = float(h / 2)
        a      = float(self._ARROW)
        left   = x
        right  = x + w

        if self._n == 1:
            pts = [(left, top), (right, top), (right, bot), (left, bot)]
        elif i == 0:
            # flat left, pointed right
            pts = [
                (left, top), (right - a, top), (right, mid),
                (right - a, bot), (left, bot),
            ]
        elif i == self._n - 1:
            # notched left, flat right
            pts = [
                (left, top), (right, top), (right, bot),
                (left, bot), (left + a, mid),
            ]
        else:
            pts = [
                (left, top), (right - a, top), (right, mid),
                (right - a, bot), (left, bot), (left + a, mid),
            ]
        return QPolygonF([QPointF(px, py) for px, py in pts])

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W  = self.width()
        H  = self.height()
        sw = W / self._n          # slot width per step

        name_font = QFont()
        name_font.setPointSize(9)

        for i in range(self._n):
            x = i * sw

            # ── fill gradient ─────────────────────────────────────────
            if i < self._active:
                c1, c2 = self._GRAD_DONE
                text_col = QColor("#ffffff")
                name_font.setBold(False)
            elif i == self._active:
                c1, c2 = self._GRAD_ACTIVE
                text_col = QColor("#111111")
                name_font.setBold(True)
            else:
                c1, c2 = self._GRAD_FUTURE
                text_col = QColor("#8888aa") if self._is_dark else QColor("#555568")
                name_font.setBold(False)

            grad = QLinearGradient(x, 0, x, H)
            grad.setColorAt(0, QColor(c1))
            grad.setColorAt(1, QColor(c2))

            poly = self._chevron_poly(i, x, sw, H)
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(poly)

            # ── step name — vertically centred ────────────────────────
            text_rect = QRect(
                int(x + (self._ARROW if i > 0 else 4)),
                0,
                int(sw - self._ARROW - (0 if i == self._n - 1 else self._ARROW) - 4),
                H,
            )
            p.setFont(name_font)
            p.setPen(text_col)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._names[i])

        p.end()
