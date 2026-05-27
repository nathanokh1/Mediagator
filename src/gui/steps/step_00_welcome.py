"""
MediaMitigator — Welcome / Intro Step (Step 0).

Shown on first launch (and every subsequent launch until the user checks
"Don't show this again").  Explains what the tool does in plain language,
shows a transfer-speed reference table, and provides a "Get Started" CTA.

Author: Nathan
"""

from __future__ import annotations

import webbrowser
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QFrame, QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

from src.gui.wizard_state import WizardState
from src.config.settings import save_settings

logger = logging.getLogger(__name__)

_GITHUB_URL = "https://github.com/your-org/MediaMitigator"   # placeholder


# ── speed reference data ─────────────────────────────────────────────────────
_SPEED_ROWS = [
    ("HDD → HDD",  "80 – 120",  "~14 min",  "~70 min",  "~2.3 hrs"),
    ("HDD → SSD",  "80 – 120",  "~14 min",  "~70 min",  "~2.3 hrs"),
    ("SSD → HDD",  "150 – 200", "~9 min",   "~45 min",  "~1.5 hrs"),
    ("SSD → SSD",  "400 – 550", "~3 min",   "~17 min",  "~35 min"),
    ("USB 3.0",    "100 – 400", "varies",   "varies",   "varies"),
]
_SPEED_HEADERS = ("Drive Type", "Typical Speed (MB/s)", "100 GB", "500 GB", "1 TB")


class WelcomeStep(QWidget):
    """Welcome / introduction screen shown before the main wizard."""

    next_requested = pyqtSignal()

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._build_ui()

    # ── build ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll, stretch=1)

        content = QWidget()
        scroll.setWidget(content)
        cl = QVBoxLayout(content)
        cl.setContentsMargins(60, 40, 60, 24)
        cl.setSpacing(24)

        # ── hero row ─────────────────────────────────────────────────────
        hero = QHBoxLayout()
        hero.setSpacing(24)

        icon_lbl = QLabel()
        icon_pix = self._load_icon(96)
        if icon_pix:
            icon_lbl.setPixmap(icon_pix)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        icon_lbl.setFixedWidth(100)
        hero.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        title = QLabel("Welcome to MediaMitigator")
        tf = QFont()
        tf.setPointSize(22)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet("color: #ff9800;")
        title_col.addWidget(title)

        tagline = QLabel(
            "A free, open-source tool that helps you move, sort, and organise "
            "your photos and videos — simply and safely."
        )
        tagline.setWordWrap(True)
        tagline.setStyleSheet("color: #cccccc; font-size: 13px;")
        title_col.addWidget(tagline)

        hero.addLayout(title_col)
        cl.addLayout(hero)

        # ── divider ───────────────────────────────────────────────────────
        cl.addWidget(_divider())

        # ── what it does — 3 bullets ──────────────────────────────────────
        what_title = _section_label("What it does")
        cl.addWidget(what_title)

        bullets = [
            ("📂", "Scan",
             "Explore any drive or folder and find every photo, video, and RAW "
             "file — no matter how deeply nested."),
            ("🗂️", "Organise",
             "Automatically sort your media by year, year/month, or file type — "
             "or move everything flat if you prefer."),
            ("✅", "Transfer",
             "Move (or copy) files safely, with real-time progress, speed stats, "
             "and a full report when it's done."),
        ]
        for icon, heading, body in bullets:
            cl.addWidget(_bullet_card(icon, heading, body))

        # ── learn more link ───────────────────────────────────────────────
        link_row = QHBoxLayout()
        link_row.setContentsMargins(0, 0, 0, 0)
        link_lbl = QLabel(
            f'For full documentation, source code, and release notes visit '
            f'<a href="{_GITHUB_URL}" style="color:#ff9800;">'
            f'the MediaMitigator GitHub repository</a>.'
        )
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setTextFormat(Qt.TextFormat.RichText)
        link_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        link_lbl.setWordWrap(True)
        link_row.addWidget(link_lbl)
        link_row.addStretch()
        cl.addLayout(link_row)

        # ── divider ───────────────────────────────────────────────────────
        cl.addWidget(_divider())

        # ── speed reference table ─────────────────────────────────────────
        speed_title = _section_label("Expected Transfer Speeds")
        speed_note = QLabel(
            "Speed is always limited by the slower drive.  "
            "Actual performance depends on file size, fragmentation, and drive health."
        )
        speed_note.setWordWrap(True)
        speed_note.setStyleSheet("color: #888; font-size: 11px;")
        cl.addWidget(speed_title)
        cl.addWidget(speed_note)
        cl.addWidget(_speed_table())

        cl.addStretch()

        # ── fixed bottom nav bar ──────────────────────────────────────────
        nav_widget = QWidget()
        nav_widget.setObjectName("navBar")
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(16, 8, 16, 8)

        # disclaimer blurb
        disclaimer = QLabel(
            "MediaMitigator is provided <b>free of charge</b> with no warranty. "
            "Use at your own risk. Contributions and donations are appreciated — "
            "they help keep this tool maintained and free."
        )
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("color: #666; font-size: 10px;")
        disclaimer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        nav_layout.addWidget(disclaimer, stretch=3)

        nav_layout.addSpacing(16)

        self._no_show_cb = QCheckBox("Don't show this again")
        self._no_show_cb.setStyleSheet("color: #888; font-size: 11px;")
        nav_layout.addWidget(self._no_show_cb)

        nav_layout.addSpacing(12)

        get_started_btn = QPushButton("Get Started  →")
        get_started_btn.setObjectName("primaryBtn")
        get_started_btn.setMinimumWidth(160)
        get_started_btn.clicked.connect(self._on_get_started)
        nav_layout.addWidget(get_started_btn)

        root.addWidget(nav_widget)

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _load_icon(size: int) -> QPixmap | None:
        from pathlib import Path
        icon_path = Path(__file__).resolve().parents[3] / "assets" / "icon_512.png"
        if icon_path.exists():
            pix = QPixmap(str(icon_path))
            return pix.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return None

    def _on_get_started(self) -> None:
        if self._no_show_cb.isChecked():
            self._state.settings["welcome_seen"] = True
            save_settings(self._state.settings)
        self.next_requested.emit()


# ── small helper widgets ─────────────────────────────────────────────────────

def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #2a2a3a;")
    return line


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    f = QFont()
    f.setPointSize(12)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet("color: #e0e0e0;")
    return lbl


def _bullet_card(icon: str, heading: str, body: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        "QFrame { background: #1a1a2e; border: 1px solid #2a2a3a; "
        "border-radius: 8px; padding: 4px; }"
    )
    row = QHBoxLayout(card)
    row.setContentsMargins(16, 14, 16, 14)
    row.setSpacing(16)

    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet("font-size: 28px;")
    icon_lbl.setFixedWidth(40)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
    row.addWidget(icon_lbl)

    text_col = QVBoxLayout()
    text_col.setSpacing(4)

    h_lbl = QLabel(heading)
    hf = QFont()
    hf.setPointSize(11)
    hf.setBold(True)
    h_lbl.setFont(hf)
    h_lbl.setStyleSheet("color: #ff9800;")
    text_col.addWidget(h_lbl)

    b_lbl = QLabel(body)
    b_lbl.setWordWrap(True)
    b_lbl.setStyleSheet("color: #cccccc; font-size: 12px;")
    text_col.addWidget(b_lbl)

    row.addLayout(text_col)
    return card


def _speed_table() -> QFrame:
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame { background: #131320; border: 1px solid #2a2a3a; border-radius: 8px; }"
    )
    grid = QVBoxLayout(frame)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(0)

    # header row
    header_row = _table_row(_SPEED_HEADERS, is_header=True)
    grid.addWidget(header_row)

    for i, row_data in enumerate(_SPEED_ROWS):
        row_widget = _table_row(row_data, is_header=False, alt=i % 2 == 1)
        grid.addWidget(row_widget)

    return frame


def _table_row(
    cols: tuple[str, ...],
    is_header: bool,
    alt: bool = False,
) -> QWidget:
    bg = "#1e1e30" if is_header else ("#181828" if alt else "#131320")
    w = QWidget()
    w.setStyleSheet(f"background: {bg};")
    row = QHBoxLayout(w)
    row.setContentsMargins(12, 8, 12, 8)
    row.setSpacing(0)

    col_widths = [160, 200, 90, 90, 90]
    for text, width in zip(cols, col_widths):
        lbl = QLabel(text)
        lbl.setFixedWidth(width)
        if is_header:
            f = QFont()
            f.setBold(True)
            f.setPointSize(10)
            lbl.setFont(f)
            lbl.setStyleSheet("color: #ff9800;")
        else:
            lbl.setStyleSheet("color: #cccccc; font-size: 11px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(lbl)

    row.addStretch()
    return w
