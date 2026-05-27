"""
Mediagator — ProgressWidget.

Rich transfer progress display with a large progress bar, color-coded
speed card, live ETA, and current-file indicator.

Author: Nathan
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.utils.date_utils import format_duration
from src.utils.file_utils import human_readable_size


# ---------------------------------------------------------------------------
# Small stat card
# ---------------------------------------------------------------------------

class _MiniCard(QFrame):
    """One metric displayed as a value + label pair."""

    def __init__(self, label: str, colour: str, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "background: #2a2a3e; border: 1px solid #3a3a5a; border-radius: 8px;"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(130)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(3)

        self._val = QLabel("—")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self._val.setFont(font)
        self._val.setStyleSheet(f"color: {colour}; border: none;")
        lay.addWidget(self._val)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #666; font-size: 10px; border: none;")
        lay.addWidget(lbl)

        self._colour = colour

    def set_value(self, text: str, colour: str | None = None) -> None:
        self._val.setText(text)
        if colour:
            self._val.setStyleSheet(f"color: {colour}; border: none;")


# ---------------------------------------------------------------------------
# Main widget
# ---------------------------------------------------------------------------

class ProgressWidget(QWidget):
    """Rich live transfer progress display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Large progress bar ─────────────────────────────────────────
        bar_frame = QFrame()
        bar_frame.setFrameShape(QFrame.Shape.StyledPanel)
        bar_frame.setStyleSheet(
            "background: #2a2a3e; border: 1px solid #3a3a5a; border-radius: 8px;"
        )
        bar_lay = QVBoxLayout(bar_frame)
        bar_lay.setContentsMargins(16, 12, 16, 12)
        bar_lay.setSpacing(6)

        # Percentage label above bar
        pct_row = QHBoxLayout()
        self._pct_label = QLabel("0%")
        pct_font = QFont()
        pct_font.setPointSize(22)
        pct_font.setBold(True)
        self._pct_label.setFont(pct_font)
        self._pct_label.setStyleSheet("color: #ff9800; border: none;")
        self._files_label = QLabel("0 / 0 files")
        self._files_label.setStyleSheet("color: #888; font-size: 12px; border: none;")
        self._files_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pct_row.addWidget(self._pct_label)
        pct_row.addStretch()
        pct_row.addWidget(self._files_label)
        bar_lay.addLayout(pct_row)

        self._overall_bar = QProgressBar()
        self._overall_bar.setRange(0, 100)
        self._overall_bar.setValue(0)
        self._overall_bar.setTextVisible(False)
        self._overall_bar.setFixedHeight(20)
        self._overall_bar.setStyleSheet("""
            QProgressBar {
                background: #1a1a2e;
                border: none;
                border-radius: 10px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff9800, stop:1 #ffb74d);
                border-radius: 10px;
            }
        """)
        bar_lay.addWidget(self._overall_bar)
        layout.addWidget(bar_frame)

        # ── Stat cards row ─────────────────────────────────────────────
        cards = QHBoxLayout()
        cards.setSpacing(10)
        self._card_speed    = _MiniCard("Current Speed",       "#2196f3")
        self._card_data     = _MiniCard("Data Transferred",    "#4caf50")
        self._card_elapsed  = _MiniCard("Elapsed",             "#ff9800")
        self._card_eta      = _MiniCard("Estimated Remaining", "#9c27b0")
        self._card_remain   = _MiniCard("Files Remaining",     "#888")
        for c in (self._card_speed, self._card_data,
                  self._card_elapsed, self._card_eta, self._card_remain):
            cards.addWidget(c)
        layout.addLayout(cards)

        # ── Current file ───────────────────────────────────────────────
        file_frame = QFrame()
        file_frame.setFrameShape(QFrame.Shape.StyledPanel)
        file_frame.setStyleSheet(
            "background: #1e1e2e; border: 1px solid #2a2a3e; border-radius: 6px;"
        )
        file_lay = QVBoxLayout(file_frame)
        file_lay.setContentsMargins(12, 8, 12, 8)
        self._current_label = QLabel("—")
        self._current_label.setWordWrap(True)
        self._current_label.setStyleSheet(
            "color: #888; font-size: 10px; font-family: monospace; border: none;"
        )
        file_lay.addWidget(self._current_label)
        layout.addWidget(file_frame)

    def update_progress(
        self,
        files_done: int,
        files_total: int,
        bytes_transferred: float,
        speed_mbs: float,
        src_path: str,
        dst_path: str,
        elapsed: float = 0.0,
    ) -> None:
        """Refresh all progress indicators."""
        pct = int((files_done / max(files_total, 1)) * 100)
        self._overall_bar.setValue(pct)
        self._pct_label.setText(f"{pct}%")
        self._files_label.setText(f"{files_done:,} / {files_total:,} files")

        # Speed card — colour-coded
        if speed_mbs >= 80:
            speed_colour = "#4caf50"   # green — fast
        elif speed_mbs >= 30:
            speed_colour = "#ff9800"   # orange — medium
        else:
            speed_colour = "#f44336"   # red — slow

        speed_str = f"{speed_mbs:.1f} MB/s" if speed_mbs > 0.5 else "—"
        self._card_speed.set_value(speed_str, speed_colour)
        self._card_data.set_value(human_readable_size(int(bytes_transferred)))
        self._card_elapsed.set_value(format_duration(elapsed))

        remaining_files = files_total - files_done
        self._card_remain.set_value(f"{remaining_files:,}")

        if speed_mbs > 0.5 and files_done > 0:
            avg_file_bytes = bytes_transferred / files_done
            remaining_secs = (avg_file_bytes * remaining_files) / (speed_mbs * 1024 * 1024)
            self._card_eta.set_value(format_duration(remaining_secs))
        else:
            self._card_eta.set_value("—")

        self._current_label.setText(f"  {src_path}\n  → {dst_path}")
