"""
MediaMitigator — Step 8: Final Report.

Generates and displays an HTML transfer report.  Provides navigation
buttons for opening the report, the destination folder, starting a new
transfer, or closing the app.

Author: Nathan
"""

import logging
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal

from src.gui.wizard_state import WizardState
from src.utils.date_utils import format_duration
from src.utils.file_utils import human_readable_size

logger = logging.getLogger(__name__)

_REPORTS_DIR = Path("reports")


def _build_html(state: WizardState) -> tuple[str, Path]:
    """Generate the HTML report string and save it to disk.

    Args:
        state: Completed wizard state with transfer_stats set.

    Returns:
        Tuple of ``(html_string, report_path)``.
    """
    stats = state.transfer_stats
    plan = state.transfer_plan
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _REPORTS_DIR.mkdir(exist_ok=True)
    report_path = _REPORTS_DIR / f"report_{ts}.html"

    # ---------- helpers ----------
    def row(label: str, value: str) -> str:
        return f"<tr><td style='padding:4px 12px 4px 0;color:#aaa'>{label}</td><td>{value}</td></tr>"

    def section(title: str, content: str) -> str:
        return (
            f"<h2 style='color:#ff9800;border-bottom:1px solid #333;padding-bottom:6px'>{title}</h2>"
            f"{content}"
        )

    # ---------- summary ----------
    if stats and plan:
        summary_rows = "".join([
            row("Files Transferred", f"{stats.files_completed:,}"),
            row("Total Size", human_readable_size(stats.bytes_transferred)),
            row("Duration", format_duration(stats.elapsed_seconds)),
            row("Average Speed", f"{stats.current_speed_mbs:.1f} MB/s"),
            row("Phases", str(plan.phase_count)),
            row("Errors", str(len(stats.errors))),
            row("Duplicates Routed", str(len(stats.duplicates))),
            row("Files Renamed", str(len(stats.renamed_files))),
        ])
        summary_html = f"<table>{summary_rows}</table>"
    else:
        summary_html = "<p>No statistics available.</p>"

    # ---------- errors ----------
    if stats and stats.flagged_items:
        error_rows = "".join(
            f"<tr>"
            f"<td style='padding:3px 8px;color:#aaa'>{ts_s}</td>"
            f"<td style='padding:3px 8px;word-break:break-all'>{src}</td>"
            f"<td style='padding:3px 8px'>{issue}</td>"
            f"<td style='padding:3px 8px;color:#f44336'>{action}</td>"
            f"</tr>"
            for ts_s, src, issue, action in stats.flagged_items
        )
        errors_html = f"<table border='0' cellspacing='0' style='width:100%'><tr style='background:#222'><th>Time</th><th>Source</th><th>Issue</th><th>Action</th></tr>{error_rows}</table>"
    else:
        errors_html = "<p style='color:#4caf50'>No errors.</p>"

    # ---------- duplicates ----------
    if stats and stats.duplicates:
        dup_lines = "".join(f"<li style='word-break:break-all'>{p}</li>" for p in stats.duplicates)
        dest_root = str(state.destination_root or "")
        dup_html = (
            f"<p>{len(stats.duplicates)} duplicate(s) routed to "
            f"<code>{dest_root}/_DUPLICATES_REVIEW/</code></p>"
            f"<ul>{dup_lines}</ul>"
        )
    else:
        dup_html = "<p style='color:#4caf50'>No duplicates detected.</p>"

    # ---------- renamed ----------
    if stats and stats.renamed_files:
        renamed_lines = "".join(
            f"<li style='word-break:break-all'>{src} → {dst}</li>"
            for src, dst in stats.renamed_files
        )
        renamed_html = f"<ul>{renamed_lines}</ul>"
    else:
        renamed_html = "<p style='color:#4caf50'>No files renamed.</p>"

    # ---------- multi-year ----------
    if plan:
        from src.models.folder_node import FolderStatus
        multi_year_nodes = [n for n in plan.folder_nodes if n.status == FolderStatus.MULTI_YEAR]
        if multi_year_nodes:
            multi_lines = "".join(
                f"<li>{n.path} → {n.destination_path}</li>"
                for n in multi_year_nodes
            )
            multi_html = f"<ul>{multi_lines}</ul>"
        else:
            multi_html = "<p style='color:#4caf50'>None.</p>"
    else:
        multi_html = "<p>—</p>"

    # ---------- lightroom ----------
    if stats and state.settings.get("lightroom_report") and stats.lightroom_paths:
        lr_lines = "".join(f"<li style='word-break:break-all'>{p}</li>" for p in stats.lightroom_paths)
        lr_html = f"<ul>{lr_lines}</ul>"
        _save_lightroom_paths(stats.lightroom_paths, ts)
    else:
        lr_html = "<p style='color:#aaa'>Lightroom report not enabled.</p>"

    # ---------- assemble ----------
    body = (
        section("Summary", summary_html)
        + section("Errors &amp; Flags", errors_html)
        + section("Duplicates", dup_html)
        + section("Renamed Files", renamed_html)
        + section("Multi-Year Folders", multi_html)
        + section("Lightroom Import Paths", lr_html)
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>MediaMitigator Report — {ts}</title>
<style>
  body {{ background:#1a1a1a; color:#e0e0e0; font-family:sans-serif; padding:32px; }}
  h1 {{ color:#ff9800; }}
  h2 {{ margin-top:32px; }}
  code {{ background:#333; padding:2px 6px; border-radius:3px; }}
  table {{ border-collapse:collapse; }}
</style>
</head>
<body>
<h1>MediaMitigator Transfer Report</h1>
<p style='color:#aaa'>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
{body}
</body>
</html>"""

    try:
        with report_path.open("w", encoding="utf-8") as fh:
            fh.write(html)
    except Exception as exc:
        logger.error("Could not save report: %s", exc)

    return html, report_path


def _save_lightroom_paths(paths: list[Path], ts: str) -> None:
    """Write Lightroom import path list to a text file.

    Args:
        paths: Destination folder paths.
        ts: Timestamp string for filename.
    """
    _REPORTS_DIR.mkdir(exist_ok=True)
    out = _REPORTS_DIR / f"lightroom_paths_{ts}.txt"
    try:
        with out.open("w", encoding="utf-8") as fh:
            for p in paths:
                fh.write(f"{p}\n")
    except Exception as exc:
        logger.error("Could not save Lightroom paths: %s", exc)


class ReportStep(QWidget):
    """Step 8 — final report display.

    Signals:
        new_transfer_requested: User wants to start over.
    """

    new_transfer_requested = pyqtSignal()

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        """Initialise the report step.

        Args:
            state: Shared wizard state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._state = state
        self._report_path: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the step layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Transfer Complete")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4caf50;")
        layout.addWidget(title)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        layout.addWidget(self._browser, stretch=1)

        # Navigation buttons
        nav = QHBoxLayout()
        self._open_report_btn = QPushButton("Open Report in Browser")
        self._open_report_btn.clicked.connect(self._open_in_browser)
        nav.addWidget(self._open_report_btn)

        self._open_dest_btn = QPushButton("Open Destination Folder")
        self._open_dest_btn.clicked.connect(self._open_destination)
        nav.addWidget(self._open_dest_btn)

        nav.addStretch()

        new_btn = QPushButton("Start New Transfer")
        new_btn.setObjectName("primaryBtn")
        new_btn.clicked.connect(self.new_transfer_requested.emit)
        nav.addWidget(new_btn)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self._close_app)
        nav.addWidget(close_btn)

        layout.addLayout(nav)

    def refresh(self) -> None:
        """Generate and display the report when the step becomes visible."""
        html, path = _build_html(self._state)
        self._report_path = path
        self._browser.setHtml(html)

    def _open_in_browser(self) -> None:
        """Open the saved HTML report in the system default browser."""
        if self._report_path and self._report_path.exists():
            webbrowser.open(self._report_path.as_uri())

    def _open_destination(self) -> None:
        """Open the destination root in Windows Explorer."""
        if self._state.destination_root:
            try:
                subprocess.Popen(["explorer", str(self._state.destination_root)])
            except Exception as exc:
                logger.warning("Could not open Explorer: %s", exc)

    def _close_app(self) -> None:
        """Close the application."""
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
