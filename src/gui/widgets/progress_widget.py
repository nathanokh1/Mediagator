"""
MediaMitigator — ProgressWidget.

Dual progress bar widget (overall + current file) with live stats labels.

Author: Nathan
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QGroupBox,
)
from PyQt6.QtCore import Qt

from src.utils.date_utils import format_duration
from src.utils.file_utils import human_readable_size


class ProgressWidget(QWidget):
    """Displays overall and per-file transfer progress with live stats.

    Intended to be embedded in Step 7 (TransferProgressStep).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the progress widget."""
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the widget layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Overall progress
        overall_box = QGroupBox("Overall Progress")
        overall_layout = QVBoxLayout(overall_box)
        self._overall_bar = QProgressBar()
        self._overall_bar.setRange(0, 100)
        self._overall_bar.setValue(0)
        self._overall_bar.setTextVisible(True)
        self._overall_bar.setFixedHeight(24)
        overall_layout.addWidget(self._overall_bar)
        layout.addWidget(overall_box)

        # Current item
        current_box = QGroupBox("Current File")
        current_layout = QVBoxLayout(current_box)
        self._current_label = QLabel("—")
        self._current_label.setWordWrap(True)
        current_layout.addWidget(self._current_label)
        layout.addWidget(current_box)

        # Stats grid
        stats_box = QGroupBox("Transfer Statistics")
        stats_layout = QVBoxLayout(stats_box)
        self._stats_labels: dict[str, QLabel] = {}
        for key in (
            "Files Completed", "Files Remaining",
            "Data Transferred", "Current Speed",
            "Elapsed", "Estimated Remaining",
        ):
            row = QHBoxLayout()
            key_lbl = QLabel(f"{key}:")
            key_lbl.setFixedWidth(160)
            val_lbl = QLabel("—")
            self._stats_labels[key] = val_lbl
            row.addWidget(key_lbl)
            row.addWidget(val_lbl)
            row.addStretch()
            stats_layout.addLayout(row)
        layout.addWidget(stats_box)

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
        """Refresh all progress indicators.

        Args:
            files_done: Number of files completed.
            files_total: Total files to transfer.
            bytes_transferred: Bytes transferred so far.
            speed_mbs: Current speed in MB/s.
            src_path: Source path of the active file.
            dst_path: Destination path of the active file.
            elapsed: Elapsed seconds since transfer started.
        """
        pct = int((files_done / max(files_total, 1)) * 100)
        self._overall_bar.setValue(pct)
        self._overall_bar.setFormat(f"{pct}%  ({files_done}/{files_total} files)")

        self._current_label.setText(f"{src_path}\n→ {dst_path}")

        remaining_files = files_total - files_done
        remaining_mb = 0.0
        if speed_mbs > 0 and files_total > 0:
            avg_file_bytes = bytes_transferred / max(files_done, 1)
            remaining_bytes = avg_file_bytes * remaining_files
            remaining_secs = remaining_bytes / (speed_mbs * 1024 * 1024)
        else:
            remaining_secs = 0.0

        self._stats_labels["Files Completed"].setText(str(files_done))
        self._stats_labels["Files Remaining"].setText(str(remaining_files))
        self._stats_labels["Data Transferred"].setText(human_readable_size(int(bytes_transferred)))
        self._stats_labels["Current Speed"].setText(f"{speed_mbs:.1f} MB/s")
        self._stats_labels["Elapsed"].setText(format_duration(elapsed))
        self._stats_labels["Estimated Remaining"].setText(format_duration(remaining_secs))
