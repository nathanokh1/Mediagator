"""
Mediagator — ScanDashboardWidget.

Rich visual summary of a completed scan.  Uses QPainter for inline
bar charts — no external charting dependencies required.

Sections:
  • Stat cards  (total files, size, images, videos, folders)
  • Image vs Video stacked bar
  • Top-5 largest folders horizontal bar chart
  • Smart insights panel (cameras, events, GPS, recommendation)

Author: Nathan
"""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPaintEvent, QFontMetrics,
)

from src.models.scan_result import ScanResult
from src.utils.file_utils import human_readable_size

# Palette
_C_ORANGE  = QColor("#ff9800")
_C_GREEN   = QColor("#4caf50")
_C_BLUE    = QColor("#2196f3")
_C_PURPLE  = QColor("#9c27b0")
_C_TEAL    = QColor("#009688")
_C_BG      = QColor("#1e1e2e")
_C_CARD    = QColor("#2a2a3e")
_C_TEXT    = QColor("#e0e0e0")
_C_DIM     = QColor("#888")
_BAR_COLOURS = [_C_ORANGE, _C_GREEN, _C_BLUE, _C_PURPLE, _C_TEAL]


# ---------------------------------------------------------------------------
# Reusable primitives
# ---------------------------------------------------------------------------

class _StatCard(QFrame):
    """Small metric card with a large number and a description label."""

    def __init__(self, label: str, value: str, colour: QColor, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"background: #2a2a3e; border: 1px solid #3a3a5a; border-radius: 8px;"
        )
        self.setMinimumWidth(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        val_lbl = QLabel(value)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        val_lbl.setFont(font)
        val_lbl.setStyleSheet(f"color: {colour.name()}; border: none;")
        layout.addWidget(val_lbl)

        desc_lbl = QLabel(label)
        desc_lbl.setStyleSheet("color: #888; font-size: 11px; border: none;")
        layout.addWidget(desc_lbl)


class _StackedBar(QWidget):
    """Horizontal stacked bar for two segments."""

    def __init__(
        self,
        label_a: str,
        value_a: int,
        colour_a: QColor,
        label_b: str,
        value_b: int,
        colour_b: QColor,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._segments = [
            (label_a, value_a, colour_a),
            (label_b, value_b, colour_b),
        ]
        self.setFixedHeight(54)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = sum(v for _, v, _ in self._segments) or 1
        bar_h = 26
        bar_y = 4
        x = 0
        w = self.width()

        for label, value, colour in self._segments:
            seg_w = int((value / total) * w)
            p.fillRect(x, bar_y, seg_w, bar_h, colour)
            if seg_w > 50:
                p.setPen(QPen(QColor("#000"), 0))
                fm = QFontMetrics(self.font())
                pct = f"{value / total * 100:.1f}%"
                p.drawText(x + 6, bar_y + bar_h - 6, pct)
            x += seg_w

        # Legend below bar
        legend_y = bar_y + bar_h + 6
        lx = 0
        for label, value, colour in self._segments:
            p.fillRect(lx, legend_y + 2, 12, 10, colour)
            p.setPen(QPen(_C_DIM))
            p.drawText(lx + 16, legend_y + 11, f"{label}: {value:,}")
            lx += 180
        p.end()


class _HBarChart(QWidget):
    """Horizontal bar chart for a list of labelled values."""

    def __init__(
        self,
        items: list[tuple[str, int]],
        unit: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._items = items
        self._unit = unit
        rows = max(len(items), 1)
        self.setFixedHeight(rows * 38 + 8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._items:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        max_val = max(v for _, v in self._items) or 1
        label_w = 220
        bar_h = 22
        row_h = 38
        gap = (row_h - bar_h) // 2

        for i, (label, value) in enumerate(self._items):
            y = i * row_h
            colour = _BAR_COLOURS[i % len(_BAR_COLOURS)]
            bar_w = int(((self.width() - label_w - 80) * value) / max_val)
            bar_w = max(bar_w, 4)

            # Label
            p.setPen(QPen(_C_TEXT))
            fm = QFontMetrics(self.font())
            truncated = fm.elidedText(label, Qt.TextElideMode.ElideMiddle, label_w - 8)
            p.drawText(0, y + gap + bar_h - 4, truncated)

            # Bar
            p.fillRect(label_w, y + gap, bar_w, bar_h, colour)

            # Value text
            p.setPen(QPen(_C_DIM))
            val_str = human_readable_size(value) if self._unit == "bytes" else f"{value:,}"
            p.drawText(label_w + bar_w + 6, y + gap + bar_h - 4, val_str)

        p.end()


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------

class ScanDashboardWidget(QWidget):
    """Full scan results dashboard with charts and smart insights.

    Call :meth:`populate` after the scan completes.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(0, 0, 8, 0)
        self._layout.setSpacing(16)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

    def populate(self, result: ScanResult, insights=None) -> None:
        """Rebuild the dashboard from scan results and optional smart insights.

        Args:
            result: Completed :class:`ScanResult`.
            insights: Optional :class:`SmartInsights` from the analyzer.
        """
        # Clear previous content
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        self._add_stat_cards(result)
        self._add_stacked_bar(result)
        self._add_top_folders_chart(result)
        if insights:
            self._add_insights_panel(insights)
        self._layout.addStretch()

    # ------------------------------------------------------------------

    def _add_stat_cards(self, result: ScanResult) -> None:
        """Add the top row of stat cards.

        Args:
            result: Scan result.
        """
        row = QHBoxLayout()
        row.setSpacing(10)
        cards = [
            ("Total Media Files", f"{result.total_files:,}", _C_ORANGE),
            ("Total Media Size",  human_readable_size(result.total_size_bytes), _C_GREEN),
            ("Images",            f"{result.image_count:,}", _C_BLUE),
            ("Videos",            f"{result.video_count:,}", _C_PURPLE),
            ("Folders w/ Media",  f"{result.folder_count:,}", _C_TEAL),
        ]
        for label, value, colour in cards:
            row.addWidget(_StatCard(label, value, colour))
        container = QWidget()
        container.setLayout(row)
        self._layout.addWidget(container)

        # Clarifying note about "Total Media Size"
        note = QLabel(
            "ℹ  <b>Total Media Size</b> = combined size of all media files found "
            "in the scanned folders.  This is the amount of data that would be transferred."
        )
        note.setWordWrap(True)
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setStyleSheet("color: #888; font-size: 11px; padding: 2px 0;")
        self._layout.addWidget(note)

    def _add_stacked_bar(self, result: ScanResult) -> None:
        """Add Images vs Videos stacked bar.

        Args:
            result: Scan result.
        """
        lbl = QLabel("Media Type Breakdown")
        lbl.setStyleSheet("font-weight: bold; color: #ff9800;")
        self._layout.addWidget(lbl)

        bar = _StackedBar(
            "Images", result.image_count, _C_BLUE,
            "Videos", result.video_count, _C_PURPLE,
        )
        self._layout.addWidget(bar)

    def _add_top_folders_chart(self, result: ScanResult) -> None:
        """Add top-5 folders horizontal bar chart.

        Args:
            result: Scan result.
        """
        if not result.top_folders:
            return
        lbl = QLabel("Top 5 Largest Folders  (by media file size)")
        lbl.setStyleSheet("font-weight: bold; color: #ff9800; margin-top: 4px;")
        self._layout.addWidget(lbl)

        items = [
            (n.name, n.total_size_bytes)
            for n in result.top_folders
        ]
        chart = _HBarChart(items, unit="bytes")
        self._layout.addWidget(chart)

    def _add_insights_panel(self, insights) -> None:
        """Add the smart insights section.

        Args:
            insights: :class:`SmartInsights` from the analyzer.
        """
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("border: 1px solid #3a3a5a;")
        self._layout.addWidget(sep)

        title = QLabel("🔍 Smart Insights  (sampled EXIF analysis)")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff9800;")
        self._layout.addWidget(title)

        # Recommendation banner
        if insights.recommendation:
            rec = QLabel(insights.recommendation)
            rec.setWordWrap(True)
            rec.setStyleSheet(
                "background: #1e3a2e; border: 1px solid #4caf50; border-radius: 6px; "
                "padding: 10px; color: #e0e0e0; font-size: 12px;"
            )
            self._layout.addWidget(rec)

        # Cameras
        if insights.top_cameras:
            cam_lbl = QLabel("📷 Detected Cameras / Devices")
            cam_lbl.setStyleSheet("font-weight: bold; margin-top: 6px;")
            self._layout.addWidget(cam_lbl)
            cam_items = [(name, count) for name, count in insights.top_cameras]
            cam_chart = _HBarChart(cam_items)
            self._layout.addWidget(cam_chart)

        # Stats row: events, GPS, year range, sampled
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        y0, y1 = insights.year_range
        year_str = f"{y0} – {y1}" if y0 and y1 else "—"
        stat_items = [
            ("Shooting Events", str(insights.event_count), _C_GREEN),
            ("Year Range", year_str, _C_BLUE),
            ("Peak Year", str(insights.peak_year or "—"), _C_ORANGE),
            ("GPS Coverage", f"{insights.gps_percent:.0f}%", _C_TEAL),
            ("Files Sampled", f"{insights.total_sampled:,}", _C_DIM),
        ]
        for label, value, colour in stat_items:
            stats_row.addWidget(_StatCard(label, value, colour))
        container = QWidget()
        container.setLayout(stats_row)
        self._layout.addWidget(container)

        # Year distribution mini-bar
        year_dist = insights.raw_stats.get("year_distribution", {})
        if year_dist:
            yr_lbl = QLabel("📅 Files per Year  (sampled)")
            yr_lbl.setStyleSheet("font-weight: bold; margin-top: 4px;")
            self._layout.addWidget(yr_lbl)
            yr_items = [(str(yr), cnt) for yr, cnt in sorted(year_dist.items())]
            yr_chart = _HBarChart(yr_items)
            self._layout.addWidget(yr_chart)
