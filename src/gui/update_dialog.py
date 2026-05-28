"""
Mediagator — Auto-Update Dialog.

Shown when a newer GitHub release is detected.  Lets the user download
and install the update in one click, or dismiss for the session.

Flow:
  1. _UpdateChecker (in main_window) fires update_available(version, url)
  2. MainWindow creates UpdateDialog and shows it
  3. "Update Now" → _DownloadWorker downloads installer to %TEMP%
  4. On success → ShellExecute runas on installer → app quits
  5. "Remind Me Later" → dialog closes, nothing is downloaded

Author: Nathan
"""

import logging
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QWidget,
)

logger = logging.getLogger(__name__)


class _DownloadWorker(QThread):
    """Background download of a URL to a local temp file.

    Signals:
        progress(int): Download progress 0-100.
        finished(str): Absolute path to the downloaded file on success.
        failed(str): Error message on failure.
    """

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    failed   = pyqtSignal(str)

    def __init__(self, url: str, dest: str, parent=None) -> None:
        super().__init__(parent)
        self._url  = url
        self._dest = dest

    def run(self) -> None:
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "Mediagator-updater"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk = 65536  # 64 KB
                with open(self._dest, "wb") as fh:
                    while True:
                        data = resp.read(chunk)
                        if not data:
                            break
                        fh.write(data)
                        downloaded += len(data)
                        if total:
                            self.progress.emit(int(downloaded * 100 / total))
            self.progress.emit(100)
            self.finished.emit(self._dest)
        except Exception as exc:
            logger.error("Update download failed: %s", exc)
            self.failed.emit(str(exc))


class UpdateDialog(QDialog):
    """Modal dialog shown when a newer Mediagator release is found.

    Args:
        version: Latest version string (e.g. ``"1.0.2"``).
        download_url: Direct URL to the installer ``.exe`` asset.
        parent: Optional parent widget.
    """

    def __init__(
        self,
        version: str,
        download_url: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._version      = version
        self._download_url = download_url
        self._worker: _DownloadWorker | None = None

        self.setWindowTitle("Update Available")
        self.setFixedWidth(440)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 20)

        # Title
        title = QLabel(f"Mediagator v{self._version} is available")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ff9800;")
        layout.addWidget(title)

        # Body text
        body = QLabel(
            "A new version is ready to install.  Click <b>Update Now</b> to "
            "download and apply it automatically — the app will restart when done."
            "<br><br>Your settings and profiles are never affected by an update."
        )
        body.setWordWrap(True)
        body.setStyleSheet("font-size: 12px; line-height: 1.4;")
        layout.addWidget(body)

        # Progress bar (hidden until download starts)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(10)
        self._progress.setStyleSheet(
            "QProgressBar { border: none; border-radius: 5px; background: #333; }"
            "QProgressBar::chunk { background: #ff9800; border-radius: 5px; }"
        )
        self._progress.hide()
        layout.addWidget(self._progress)

        # Status label
        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 11px; color: #888;")
        self._status.hide()
        layout.addWidget(self._status)

        layout.addSpacing(4)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._later_btn = QPushButton("Remind Me Later")
        self._later_btn.setFixedHeight(34)
        self._later_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #555; "
            "border-radius: 4px; padding: 0 16px; color: #aaa; }"
            "QPushButton:hover { border-color: #aaa; color: #fff; }"
        )
        self._later_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._later_btn)

        btn_row.addSpacing(8)

        self._update_btn = QPushButton("⬆  Update Now")
        self._update_btn.setFixedHeight(34)
        self._update_btn.setStyleSheet(
            "QPushButton { background: #ff9800; color: #000; font-weight: bold; "
            "border-radius: 4px; padding: 0 20px; border: none; }"
            "QPushButton:hover { background: #ffb74d; }"
            "QPushButton:disabled { background: #555; color: #888; }"
        )
        self._update_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self._update_btn)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Download flow
    # ------------------------------------------------------------------

    def _start_download(self) -> None:
        """Begin downloading the installer to a temp file."""
        self._update_btn.setEnabled(False)
        self._later_btn.setEnabled(False)
        self._update_btn.setText("Downloading…")
        self._progress.show()
        self._status.setText("Downloading installer…")
        self._status.show()

        filename = f"Mediagator_Setup_{self._version}.exe"
        dest = os.path.join(tempfile.gettempdir(), filename)

        self._worker = _DownloadWorker(self._download_url, dest)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_download_done)
        self._worker.failed.connect(self._on_download_failed)
        self._worker.start()
        logger.info("Downloading update v%s from %s", self._version, self._download_url)

    def _on_download_done(self, path: str) -> None:
        """Launch the downloaded installer and quit the app."""
        self._status.setText("Launching installer — the app will close now…")
        self._update_btn.setText("Installing…")
        logger.info("Update downloaded to %s — launching installer", path)

        try:
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", path, None, None, 1
                )
            else:
                import subprocess
                subprocess.Popen([path])
        except Exception as exc:
            logger.error("Failed to launch installer: %s", exc)
            self._on_download_failed(str(exc))
            return

        # Give the installer a moment to start, then quit
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(800, self._quit_for_update)

    def _quit_for_update(self) -> None:
        """Close the dialog and quit the application for the installer."""
        self.accept()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def _on_download_failed(self, error: str) -> None:
        """Show error state and re-enable the retry button."""
        self._progress.hide()
        self._status.setText(f"Download failed: {error}")
        self._status.setStyleSheet("font-size: 11px; color: #ef5350;")
        self._update_btn.setText("⬆  Retry")
        self._update_btn.setEnabled(True)
        self._later_btn.setEnabled(True)
        logger.error("Update download failed: %s", error)

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(2000)
        super().closeEvent(event)
