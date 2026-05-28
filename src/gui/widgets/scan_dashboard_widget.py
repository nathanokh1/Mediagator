"""
Mediagator — ScanDashboardWidget (tabbed).

Five-tab rich analysis of a completed scan:
  1. Overview  — summary cards, media-type bar, top folders
  2. Timeline  — year-by-year distribution chart
  3. File Types — per-extension breakdown
  4. Stale Data — files by last-modified age with archive action
  5. Folder Intel — deepest / largest / most-files folders

Author: Nathan
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPaintEvent, QFontMetrics,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QTabWidget, QPushButton, QGridLayout,
)

from src.models.scan_result import ScanResult
from src.utils.file_utils import human_readable_size

# Palette
_ORANGE  = QColor("#ff9800")
_GREEN   = QColor("#4caf50")
_BLUE    = QColor("#2196f3")
_PURPLE  = QColor("#9c27b0")
_TEAL    = QColor("#009688")
_AMBER   = QColor("#ffc107")
_RED     = QColor("#ef5350")
_INDIGO  = QColor("#3f51b5")
_BAR_COLOURS = [_ORANGE, _GREEN, _BLUE, _PURPLE, _TEAL, _AMBER, _RED, _INDIGO,
                QColor("#e91e63"), QColor("#00bcd4"), QColor("#8bc34a"), QColor("#ff5722")]


# ---------------------------------------------------------------------------
# Reusable primitives
# ---------------------------------------------------------------------------

class _StatCard(QFrame):
    """Single metric card: big coloured number + label."""

    def __init__(self, value: str, label: str, colour: QColor, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setStyleSheet(
            "QFrame#statCard { background: #2a2a3e; border-radius: 8px; }"
        )
        self.setMinimumSize(130, 80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {colour.name()}; font-size: 22px; font-weight: bold;")
        lay.addWidget(val_lbl)

        lbl = QLabel(label)
        lbl.setObjectName("hintLabel")
        lbl.setStyleSheet("font-size: 11px;")
        lay.addWidget(lbl)


class _HBarChart(QWidget):
    """Horizontal bar chart rendered with QPainter — no external dependencies."""

    _ROW_H  = 28
    _GAP    = 4
    _LABEL_W = 180
    _VAL_W   = 80

    def __init__(
        self,
        rows: list[tuple[str, int, int]],   # (label, value, total) — value/total drives width
        colours: list[QColor],
        fmt_fn=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._rows    = rows
        self._colours = colours
        self._fmt     = fmt_fn or (lambda v: str(v))
        n = len(rows)
        self.setFixedHeight(max(60, n * (self._ROW_H + self._GAP) + self._GAP))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event: QPaintEvent) -> None:
        if not self._rows:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()
        bar_area = W - self._LABEL_W - self._VAL_W - 16
        text_col = self.palette().text().color()
        dim_col  = self.palette().mid().color()
        font = QFont(); font.setPointSize(9)
        p.setFont(font)

        max_val = max((r[1] for r in self._rows), default=1) or 1
        for i, (label, val, _total) in enumerate(self._rows):
            y = self._GAP + i * (self._ROW_H + self._GAP)
            col = self._colours[i % len(self._colours)]

            # Label
            p.setPen(text_col)
            lbl_rect = QRect(0, y, self._LABEL_W - 8, self._ROW_H)
            fm = QFontMetrics(font)
            elided = fm.elidedText(label, Qt.TextElideMode.ElideMiddle, self._LABEL_W - 8)
            p.drawText(lbl_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)

            # Bar
            bar_w = int(bar_area * val / max_val) if max_val else 0
            bar_rect = QRect(self._LABEL_W, y + 4, bar_w, self._ROW_H - 8)
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(bar_rect, 3, 3)

            # Value label
            p.setPen(dim_col)
            val_rect = QRect(self._LABEL_W + bar_area + 4, y, self._VAL_W, self._ROW_H)
            p.drawText(val_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       self._fmt(val))

        p.end()


class _StackedBar(QWidget):
    """Single horizontal stacked bar for image vs video breakdown."""

    _H = 28

    def __init__(self, images: int, videos: int, parent=None) -> None:
        super().__init__(parent)
        self._images = images
        self._videos = videos
        self.setFixedHeight(self._H + 28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event: QPaintEvent) -> None:
        total = self._images + self._videos
        if total == 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()
        font = QFont(); font.setPointSize(9)
        p.setFont(font)

        img_w = int(W * self._images / total)
        vid_w = W - img_w

        p.setBrush(QBrush(_BLUE)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRect(0, 0, img_w, self._H), 4, 4)
        p.setBrush(QBrush(_PURPLE)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRect(img_w, 0, vid_w, self._H), 4, 4)

        legend_col = self.palette().text().color()
        p.setPen(legend_col)
        pct_img = self._images * 100 // total
        p.drawText(QRect(0, self._H + 4, W // 2, 20),
                   Qt.AlignmentFlag.AlignLeft,
                   f"■ Images: {self._images:,}  ({pct_img}%)")
        p.drawText(QRect(W // 2, self._H + 4, W // 2, 20),
                   Qt.AlignmentFlag.AlignLeft,
                   f"■ Videos: {self._videos:,}  ({100 - pct_img}%)")
        p.end()


def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #ff9800; margin-top: 8px;")
    return lbl


def _scrollable(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidget(inner)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return sa


# ---------------------------------------------------------------------------
# Individual tab content builders
# ---------------------------------------------------------------------------

def _build_overview(result: ScanResult) -> QWidget:
    """Tab 1 — Summary cards, media type bar, top 10 folders."""
    root = QWidget()
    lay = QVBoxLayout(root)
    lay.setContentsMargins(0, 8, 0, 8)
    lay.setSpacing(10)

    # Stat cards
    cards_row = QHBoxLayout()
    cards_row.setSpacing(8)
    cards = [
        (_StatCard(f"{result.total_files:,}",   "Total Media Files",  _ORANGE)),
        (_StatCard(human_readable_size(result.total_size_bytes), "Total Media Size", _GREEN)),
        (_StatCard(f"{result.image_count:,}",   "Images",             _BLUE)),
        (_StatCard(f"{result.video_count:,}",   "Videos",             _PURPLE)),
        (_StatCard(f"{result.folder_count:,}",  "Folders w/ Media",   _TEAL)),
    ]
    for c in cards:
        cards_row.addWidget(c)
    lay.addLayout(cards_row)

    note = QLabel(
        "ℹ  Total Media Size = combined size of all media files found. "
        "This is the amount of data that would be transferred."
    )
    note.setWordWrap(True)
    note.setObjectName("hintLabel")
    note.setStyleSheet("font-size: 10px; padding: 2px 0;")
    lay.addWidget(note)

    # Image vs Video bar
    if result.total_files > 0:
        lay.addWidget(_section("Media Type Breakdown"))
        lay.addWidget(_StackedBar(result.image_count, result.video_count))

    # Top 10 folders
    if result.top_folders:
        lay.addWidget(_section("Top 10 Largest Folders  (by media file size)"))
        rows = [(n.path.name, n.total_size_bytes, result.total_size_bytes)
                for n in result.top_folders]
        lay.addWidget(_HBarChart(rows, _BAR_COLOURS,
                                  fmt_fn=human_readable_size))

    lay.addStretch()

    container = QWidget()
    cl = QVBoxLayout(container)
    cl.setContentsMargins(16, 0, 16, 0)
    cl.addWidget(root)
    return _scrollable(container)


def _build_timeline(result: ScanResult) -> QWidget:
    """Tab 2 — Year-by-year file distribution."""
    root = QWidget()
    lay = QVBoxLayout(root)
    lay.setContentsMargins(0, 8, 0, 8)
    lay.setSpacing(10)

    if not result.year_dist:
        lay.addWidget(QLabel("No date information available."))
        lay.addStretch()
        return _scrollable(root)

    lay.addWidget(_section("Files by Year  (based on last-modified date)"))

    years = sorted(result.year_dist.keys())
    rows_count = [(str(y), result.year_dist[y][0], max(v[0] for v in result.year_dist.values()))
                  for y in years]
    rows_size  = [(str(y), result.year_dist[y][1], max(v[1] for v in result.year_dist.values()))
                  for y in years]

    lbl_c = QLabel("File Count")
    lbl_c.setStyleSheet("font-size: 11px; font-weight: bold; margin-top: 4px;")
    lay.addWidget(lbl_c)
    chart_c = _HBarChart(rows_count, [_BLUE] * len(years),
                          fmt_fn=lambda v: f"{v:,} files")
    chart_c.setFixedHeight(len(years) * 32 + 8)
    lay.addWidget(chart_c)

    lbl_s = QLabel("Storage Size")
    lbl_s.setStyleSheet("font-size: 11px; font-weight: bold; margin-top: 8px;")
    lay.addWidget(lbl_s)
    chart_s = _HBarChart(rows_size, [_ORANGE] * len(years),
                          fmt_fn=human_readable_size)
    chart_s.setFixedHeight(len(years) * 32 + 8)
    lay.addWidget(chart_s)

    # Summary stats
    oldest = min(years)
    newest = max(years)
    peak_y = max(result.year_dist, key=lambda y: result.year_dist[y][0])
    summary = QLabel(
        f"📅  Library spans <b>{oldest}</b> → <b>{newest}</b>  "
        f"({newest - oldest + 1} years)    "
        f"·    Peak year: <b>{peak_y}</b> "
        f"({result.year_dist[peak_y][0]:,} files)"
    )
    summary.setWordWrap(True)
    summary.setStyleSheet("font-size: 12px; margin-top: 8px; padding: 6px; "
                          "background: #2a2a3e; border-radius: 6px;")
    lay.addWidget(summary)
    lay.addStretch()

    container = QWidget()
    cl = QVBoxLayout(container)
    cl.setContentsMargins(16, 0, 16, 0)
    cl.addWidget(root)
    return _scrollable(container)


def _build_file_types(result: ScanResult) -> QWidget:
    """Tab 3 — Per-extension breakdown sorted by size."""
    root = QWidget()
    lay = QVBoxLayout(root)
    lay.setContentsMargins(0, 8, 0, 8)
    lay.setSpacing(10)

    if not result.ext_stats:
        lay.addWidget(QLabel("No file type data available."))
        lay.addStretch()
        return _scrollable(root)

    lay.addWidget(_section("File Types  (sorted by storage size)"))

    sorted_exts = sorted(result.ext_stats.items(), key=lambda kv: kv[1][1], reverse=True)
    max_bytes = sorted_exts[0][1][1] if sorted_exts else 1

    rows_size  = [(ext.lstrip(".").upper(), kv[1], max_bytes) for ext, kv in sorted_exts]
    rows_count = [(ext.lstrip(".").upper(), kv[0], max(v[0] for _, v in sorted_exts))
                  for ext, kv in sorted_exts]

    lbl_s = QLabel("Storage Size per Type")
    lbl_s.setStyleSheet("font-size: 11px; font-weight: bold;")
    lay.addWidget(lbl_s)
    chart_s = _HBarChart(rows_size, _BAR_COLOURS, fmt_fn=human_readable_size)
    chart_s.setFixedHeight(len(sorted_exts) * 32 + 8)
    lay.addWidget(chart_s)

    lbl_c = QLabel("File Count per Type")
    lbl_c.setStyleSheet("font-size: 11px; font-weight: bold; margin-top: 8px;")
    lay.addWidget(lbl_c)
    chart_c = _HBarChart(rows_count, _BAR_COLOURS, fmt_fn=lambda v: f"{v:,}")
    chart_c.setFixedHeight(len(sorted_exts) * 32 + 8)
    lay.addWidget(chart_c)

    lay.addStretch()

    container = QWidget()
    cl = QVBoxLayout(container)
    cl.setContentsMargins(16, 0, 16, 0)
    cl.addWidget(root)
    return _scrollable(container)


def _build_stale(result: ScanResult, on_archive) -> QWidget:
    """Tab 4 — Stale data by last-modified age with action buttons."""
    root = QWidget()
    lay = QVBoxLayout(root)
    lay.setContentsMargins(16, 8, 16, 8)
    lay.setSpacing(10)

    lay.addWidget(_section("Stale Data  (by last-modified date)"))

    intro = QLabel(
        "Files that haven't been modified in a long time are good candidates "
        "for archiving to a cold-storage drive or deletion.\n"
        "Click <b>Archive</b> to route these folders into a new transfer."
    )
    intro.setWordWrap(True)
    intro.setObjectName("hintLabel")
    intro.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
    lay.addWidget(intro)

    buckets = [
        ("3m+",  "Not modified in 3+ months",  _AMBER),
        ("6m+",  "Not modified in 6+ months",  _ORANGE),
        ("1y+",  "Not modified in 1+ year",    _RED),
        ("2y+",  "Not modified in 2+ years",   QColor("#b71c1c")),
    ]

    for key, label, col in buckets:
        data = result.stale_buckets.get(key, [0, 0])
        count, size = data[0], data[1]
        folders = result.stale_folders.get(key, set())

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #2a2a3e; border-radius: 8px; border-left: 4px solid "
            + col.name() + "; }"
        )
        card_lay = QHBoxLayout(card)
        card_lay.setContentsMargins(14, 10, 14, 10)

        info = QVBoxLayout()
        title_lbl = QLabel(label)
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {col.name()};")
        info.addWidget(title_lbl)

        stat_lbl = QLabel(
            f"{count:,} files  ·  {human_readable_size(size)}  "
            f"·  {len(folders)} folder{'s' if len(folders) != 1 else ''}"
            if count else "No stale files found in this range."
        )
        stat_lbl.setObjectName("hintLabel")
        stat_lbl.setStyleSheet("font-size: 11px;")
        info.addWidget(stat_lbl)

        card_lay.addLayout(info, stretch=1)

        if count > 0:
            btn = QPushButton("Archive →")
            btn.setFixedSize(100, 32)
            btn.setStyleSheet(
                f"QPushButton {{ background: {col.name()}; color: #000; font-weight: bold; "
                f"border-radius: 4px; border: none; }}"
                f"QPushButton:hover {{ background: #ffb74d; }}"
            )
            folder_list = list(folders)
            btn.clicked.connect(lambda _, fl=folder_list, bk=key: on_archive(fl, bk))
            card_lay.addWidget(btn)

        lay.addWidget(card)

    lay.addStretch()
    container = QWidget()
    cl = QVBoxLayout(container)
    cl.setContentsMargins(0, 0, 0, 0)
    cl.addWidget(root)
    return _scrollable(container)


def _build_folder_intel(result: ScanResult) -> QWidget:
    """Tab 5 — Largest folders, deepest paths, most-files folders."""
    root = QWidget()
    lay = QVBoxLayout(root)
    lay.setContentsMargins(0, 8, 0, 8)
    lay.setSpacing(10)

    # Top 10 by size
    if result.top_folders:
        lay.addWidget(_section("Top 10 Largest Folders"))
        rows = [(f"{n.path.name}  ({n.path.parent.name})",
                 n.total_size_bytes,
                 result.total_size_bytes or 1)
                for n in result.top_folders]
        chart = _HBarChart(rows, _BAR_COLOURS, fmt_fn=human_readable_size)
        chart.setFixedHeight(len(rows) * 32 + 8)
        lay.addWidget(chart)

    # Top 10 by file count
    if result.folder_nodes:
        lay.addWidget(_section("Most Files in a Single Folder"))
        top_count = sorted(result.folder_nodes,
                           key=lambda n: n.file_count, reverse=True)[:10]
        max_c = top_count[0].file_count if top_count else 1
        rows_c = [(f"{n.path.name}  ({n.path.parent.name})",
                   n.file_count, max_c)
                  for n in top_count]
        chart_c = _HBarChart(rows_c, [_TEAL] * 10, fmt_fn=lambda v: f"{v:,} files")
        chart_c.setFixedHeight(len(rows_c) * 32 + 8)
        lay.addWidget(chart_c)

    # Deep folders
    if result.deep_folders:
        lay.addWidget(_section("Deeply Nested Folders  (may be forgotten data)"))
        for path, depth in result.deep_folders[:10]:
            lbl = QLabel(f"  Depth {depth}  ·  {path}")
            lbl.setObjectName("hintLabel")
            lbl.setStyleSheet("font-size: 10px; font-family: monospace;")
            lbl.setWordWrap(True)
            lay.addWidget(lbl)

    lay.addStretch()

    container = QWidget()
    cl = QVBoxLayout(container)
    cl.setContentsMargins(16, 0, 16, 0)
    cl.addWidget(root)
    return _scrollable(container)


# ---------------------------------------------------------------------------
# Main widget
# ---------------------------------------------------------------------------

class ScanDashboardWidget(QWidget):
    """Tabbed scan analysis dashboard.

    Signals:
        stale_route_requested(list[Path], str):
            Emitted when user clicks Archive on a stale bucket.
            Carries (folder_paths, bucket_key).
    """

    stale_route_requested = pyqtSignal(list, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result: ScanResult | None = None
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setStyleSheet(
            "QTabBar::tab { padding: 8px 18px; font-size: 12px; }"
            "QTabBar::tab:selected { color: #ff9800; border-bottom: 2px solid #ff9800; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._tabs)

    def populate(self, result: ScanResult, insights: Any = None) -> None:
        """Populate all tabs from a completed scan result.

        Args:
            result: Completed :class:`ScanResult`.
            insights: Optional :class:`SmartInsights` (used in overview).
        """
        self._result = result
        self._tabs.clear()

        self._tabs.addTab(_build_overview(result),    "📊  Overview")
        self._tabs.addTab(_build_timeline(result),    "📅  Timeline")
        self._tabs.addTab(_build_file_types(result),  "🗂  File Types")
        self._tabs.addTab(_build_stale(result, self._on_archive), "🕰  Stale Data")
        self._tabs.addTab(_build_folder_intel(result), "📁  Folder Intel")

    def _on_archive(self, folders: list[Path], bucket: str) -> None:
        self.stale_route_requested.emit(folders, bucket)
