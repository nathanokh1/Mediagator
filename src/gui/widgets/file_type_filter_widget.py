"""
MediaMitigator — FileTypeFilterWidget.

Collapsible grouped file-type selector for the Drive Selection step.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  File Types to Scan                      [▼ collapse]│
  ├─────────────────────────────────────────────────────┤
  │  📷 Photos          [All] [None]                     │
  │   ☑ JPG/JPEG  ☑ PNG  ☑ HEIC  ☑ GIF  ☑ WEBP  ☑ BMP  │
  ├─────────────────────────────────────────────────────┤
  │  📸 RAW / Professional   [All] [None]                │
  │   ☑ RAW  ☑ CR2/CR3  ☑ NEF  ☑ ARW  ☑ DNG  ☑ TIFF    │
  ├─────────────────────────────────────────────────────┤
  │  🎬 Videos          [All] [None]                     │
  │   ☑ MP4  ☑ MOV  ☑ AVI  ☑ MKV  ☑ MTS  ☑ MXF  ☑ LRV  │
  └─────────────────────────────────────────────────────┘

The widget emits ``extensions_changed(set[str])`` whenever any checkbox
is toggled.

Author: Nathan
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QGridLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.config.constants import FILE_TYPE_GROUPS, DEFAULT_SELECTED_EXTENSIONS


class _GroupPanel(QFrame):
    """One collapsible group (Photos / RAW / Videos).

    Signals:
        changed: Emitted whenever any checkbox in the group toggles.
    """

    changed = pyqtSignal()

    def __init__(self, group: dict, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #242436; border: 1px solid #3a3a5a; border-radius: 6px; }"
        )

        self._checkboxes: list[tuple[QCheckBox, list[str]]] = []
        self._group = group
        self._blocked = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 8)
        layout.setSpacing(6)

        # ── Header row ──────────────────────────────────────────────
        header = QHBoxLayout()

        # Group tri-state checkbox
        self._group_cb = QCheckBox()
        self._group_cb.setTristate(True)
        self._group_cb.setChecked(True)
        self._group_cb.stateChanged.connect(self._on_group_toggled)
        header.addWidget(self._group_cb)

        lbl = QLabel(self._group["name"])
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        lbl.setFont(font)
        lbl.setStyleSheet("border: none; background: transparent; color: #e0e0e0;")
        header.addWidget(lbl)
        header.addStretch()

        all_btn = QPushButton("All")
        all_btn.setFixedSize(40, 22)
        all_btn.setStyleSheet(
            "QPushButton { background: #3a3a5a; border: 1px solid #555; "
            "border-radius: 3px; color: #4caf50; font-size: 10px; }"
            "QPushButton:hover { background: #4a4a7a; }"
        )
        all_btn.clicked.connect(self._select_all)
        header.addWidget(all_btn)

        none_btn = QPushButton("None")
        none_btn.setFixedSize(44, 22)
        none_btn.setStyleSheet(
            "QPushButton { background: #3a3a5a; border: 1px solid #555; "
            "border-radius: 3px; color: #f44336; font-size: 10px; }"
            "QPushButton:hover { background: #4a4a7a; }"
        )
        none_btn.clicked.connect(self._select_none)
        header.addWidget(none_btn)

        layout.addLayout(header)

        # ── Checkbox grid ────────────────────────────────────────────
        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(self._grid_widget)
        grid.setContentsMargins(22, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)

        cols = 4
        for idx, item in enumerate(self._group["items"]):
            cb = QCheckBox(item["label"])
            cb.setChecked(item["default"])
            cb.setStyleSheet("QCheckBox { border: none; background: transparent; color: #ccc; }")
            cb.stateChanged.connect(self._on_child_changed)
            grid.addWidget(cb, idx // cols, idx % cols)
            self._checkboxes.append((cb, item["exts"]))

        layout.addWidget(self._grid_widget)

    # ------------------------------------------------------------------

    def _on_group_toggled(self, state: int) -> None:
        """Cascade group checkbox to all children (skip partial)."""
        if self._blocked:
            return
        if state == Qt.CheckState.PartiallyChecked.value:
            return
        checked = (state == Qt.CheckState.Checked.value)
        self._blocked = True
        for cb, _ in self._checkboxes:
            cb.setChecked(checked)
        self._blocked = False
        self.changed.emit()

    def _on_child_changed(self) -> None:
        """Sync group tri-state from children and emit changed."""
        if self._blocked:
            return
        total = len(self._checkboxes)
        checked_count = sum(1 for cb, _ in self._checkboxes if cb.isChecked())
        self._blocked = True
        if checked_count == 0:
            self._group_cb.setCheckState(Qt.CheckState.Unchecked)
        elif checked_count == total:
            self._group_cb.setCheckState(Qt.CheckState.Checked)
        else:
            self._group_cb.setCheckState(Qt.CheckState.PartiallyChecked)
        self._blocked = False
        self.changed.emit()

    def _select_all(self) -> None:
        self._blocked = True
        for cb, _ in self._checkboxes:
            cb.setChecked(True)
        self._group_cb.setCheckState(Qt.CheckState.Checked)
        self._blocked = False
        self.changed.emit()

    def _select_none(self) -> None:
        self._blocked = True
        for cb, _ in self._checkboxes:
            cb.setChecked(False)
        self._group_cb.setCheckState(Qt.CheckState.Unchecked)
        self._blocked = False
        self.changed.emit()

    def get_selected_extensions(self) -> set[str]:
        """Return all checked extensions from this group.

        Returns:
            Set of lowercase extension strings.
        """
        result: set[str] = set()
        for cb, exts in self._checkboxes:
            if cb.isChecked():
                result.update(exts)
        return result

    def set_selected_extensions(self, selected: set[str]) -> None:
        """Apply a set of selected extensions, checking matching boxes.

        Args:
            selected: Extensions that should be checked.
        """
        self._blocked = True
        for cb, exts in self._checkboxes:
            cb.setChecked(any(e in selected for e in exts))
        self._blocked = False
        self._on_child_changed()


# ---------------------------------------------------------------------------
# Main public widget
# ---------------------------------------------------------------------------

class FileTypeFilterWidget(QWidget):
    """Collapsible multi-group file type filter panel.

    Signals:
        extensions_changed(set[str]): Emits the full set of checked extensions
            whenever any checkbox changes.
    """

    extensions_changed = pyqtSignal(set)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._panels: list[_GroupPanel] = []
        self._collapsed = False
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Title bar (always visible) ────────────────────────────────
        title_bar = QFrame()
        title_bar.setStyleSheet(
            "QFrame { background: #2a2a3e; border: 1px solid #3a3a5a; "
            "border-radius: 6px 6px 0 0; }"
        )
        title_bar.setFixedHeight(36)
        title_row = QHBoxLayout(title_bar)
        title_row.setContentsMargins(12, 0, 8, 0)

        title_lbl = QLabel("File Types to Scan")
        font = QFont()
        font.setBold(True)
        title_lbl.setFont(font)
        title_lbl.setStyleSheet("border: none; background: transparent; color: #ff9800;")
        title_row.addWidget(title_lbl)

        self._ext_count_lbl = QLabel("")
        self._ext_count_lbl.setStyleSheet(
            "border: none; background: transparent; color: #888; font-size: 11px;"
        )
        title_row.addWidget(self._ext_count_lbl)
        title_row.addStretch()

        # Quick preset buttons
        for label, fn_name, colour in (
            ("All Types", "_preset_all", "#4caf50"),
            ("Photos Only", "_preset_photos", "#2196f3"),
            ("Videos Only", "_preset_videos", "#9c27b0"),
            ("RAW Only", "_preset_raw", "#ff9800"),
        ):
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton {{ background: #1e1e2e; border: 1px solid {colour}; "
                f"border-radius: 3px; color: {colour}; font-size: 10px; padding: 0 8px; }}"
                f"QPushButton:hover {{ background: #2a2a4e; }}"
            )
            btn.clicked.connect(getattr(self, fn_name))
            title_row.addWidget(btn)
            title_row.addSpacing(4)

        self._toggle_btn = QPushButton("▼")
        self._toggle_btn.setFixedSize(28, 24)
        self._toggle_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #aaa; font-size: 12px; }"
            "QPushButton:hover { color: #fff; }"
        )
        self._toggle_btn.clicked.connect(self._toggle_collapse)
        title_row.addWidget(self._toggle_btn)
        outer.addWidget(title_bar)

        # ── Collapsible content area ──────────────────────────────────
        self._content = QWidget()
        self._content.setStyleSheet(
            "QWidget { background: #1e1e2e; border: 1px solid #3a3a5a; "
            "border-top: none; border-radius: 0 0 6px 6px; }"
        )
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)

        for group in FILE_TYPE_GROUPS:
            panel = _GroupPanel(group)
            panel.changed.connect(self._on_any_changed)
            self._panels.append(panel)
            content_layout.addWidget(panel)

        outer.addWidget(self._content)
        self._on_any_changed()  # init count label

    # ------------------------------------------------------------------
    # Collapse / expand
    # ------------------------------------------------------------------

    def _toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        self._toggle_btn.setText("▶" if self._collapsed else "▼")

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def _apply_preset(self, selected: set[str]) -> None:
        for panel in self._panels:
            panel.set_selected_extensions(selected)

    def _preset_all(self) -> None:
        self._apply_preset(DEFAULT_SELECTED_EXTENSIONS)

    def _preset_photos(self) -> None:
        from src.config.constants import IMAGE_EXTENSIONS
        self._apply_preset(IMAGE_EXTENSIONS)

    def _preset_videos(self) -> None:
        from src.config.constants import VIDEO_EXTENSIONS
        self._apply_preset(VIDEO_EXTENSIONS)

    def _preset_raw(self) -> None:
        self._apply_preset({".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng", ".tiff", ".tif"})

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _on_any_changed(self) -> None:
        exts = self.get_selected_extensions()
        count = len(exts)
        self._ext_count_lbl.setText(
            f"  ({count} extension{'s' if count != 1 else ''} selected)"
        )
        self.extensions_changed.emit(exts)

    def get_selected_extensions(self) -> set[str]:
        """Return the combined set of all checked extensions.

        Returns:
            Set of lowercase extension strings (e.g. ``{'.jpg', '.mp4'}``.
        """
        result: set[str] = set()
        for panel in self._panels:
            result.update(panel.get_selected_extensions())
        return result

    def set_selected_extensions(self, selected: set[str]) -> None:
        """Restore a previously saved extension selection.

        Args:
            selected: Extensions to check (all others unchecked).
        """
        for panel in self._panels:
            panel.set_selected_extensions(selected)
