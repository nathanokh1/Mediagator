"""
MediaMitigator — Logging configuration.

Two log outputs:
  1. Console (stdout)  — DEBUG level, development visibility.
  2. logs/app.log      — INFO+ level, persistent app-level log, rotates at
                         5 MB, keeps 3 backups.  Uses a QueueHandler so file
                         writes never block the GUI thread.

Per-transfer file loggers (logs/transfer_<ts>.log) are created separately
via :func:`get_transfer_logger` and used only during active transfers.

Author: Nathan
"""

import logging
import logging.handlers
import queue
import sys
from datetime import datetime
from pathlib import Path

from src.config.constants import LOG_FORMAT, LOG_DATE_FORMAT

_LOGS_DIR = Path("logs")
_APP_LOG   = _LOGS_DIR / "app.log"

# Module-level async queue + listener (created once on first call to setup_logging)
_log_queue: queue.Queue | None = None
_queue_listener: logging.handlers.QueueListener | None = None


def setup_logging(level: int = logging.DEBUG) -> None:
    """Configure the root logger with a console handler and an async file handler.

    Safe to call multiple times — extra calls are no-ops once handlers exist.

    Args:
        level: Minimum log level shown on the console.
    """
    global _log_queue, _queue_listener

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Already configured — nothing to do
    if root.handlers:
        return

    _LOGS_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # ── Console handler (synchronous, lightweight) ────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)

    # ── Rotating file handler (writes to disk) ────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        _APP_LOG,
        maxBytes=5 * 1024 * 1024,   # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)

    # ── Async queue so file I/O never blocks the GUI thread ───────────
    _log_queue = queue.Queue(maxsize=10_000)
    queue_handler = logging.handlers.QueueHandler(_log_queue)
    queue_handler.setLevel(logging.DEBUG)

    # The QueueListener runs in its own daemon thread and drains the queue
    _queue_listener = logging.handlers.QueueListener(
        _log_queue,
        console,
        file_handler,
        respect_handler_level=True,
    )
    _queue_listener.start()

    root.addHandler(queue_handler)

    # Log the startup so app.log always shows when the app was launched
    root.info(
        "=" * 60 + "\n  MediaMitigator started  %s\n" + "=" * 60,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def shutdown_logging() -> None:
    """Stop the async queue listener cleanly (call on app exit)."""
    global _queue_listener
    if _queue_listener:
        _queue_listener.stop()
        _queue_listener = None


def get_transfer_logger(timestamp: str | None = None) -> logging.Logger:
    """Create (or retrieve) a file logger for the current transfer session.

    Writes to ``logs/transfer_<timestamp>.log`` at DEBUG level.  The logger
    also propagates to the root (so transfer events appear in app.log too).

    Args:
        timestamp: Optional timestamp string for the log filename.

    Returns:
        A :class:`logging.Logger` dedicated to this transfer session.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger_name = f"transfer_{timestamp}"
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return logger

    _LOGS_DIR.mkdir(exist_ok=True)
    log_path = _LOGS_DIR / f"transfer_{timestamp}.log"

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    return logger


def log_operation(
    logger: logging.Logger,
    level: int,
    operation: str,
    source: Path | str,
    dest: Path | str | None,
    size_bytes: int | None,
    result: str,
    note: str = "",
) -> None:
    """Emit a structured file-operation log entry.

    Args:
        logger: Target logger.
        level: Log level (e.g. ``logging.INFO``).
        operation: Operation type (e.g. ``COPY``, ``DELETE``, ``SKIP``).
        source: Source file or folder path.
        dest: Destination path, or ``None`` if not applicable.
        size_bytes: File size, or ``None`` if not known.
        result: Outcome string (e.g. ``SUCCESS``, ``ERROR``, ``SKIPPED``).
        note: Optional free-form annotation.
    """
    dest_str = str(dest) if dest else "—"
    size_str = f"{size_bytes:,}B" if size_bytes is not None else "—"
    note_str = f" | {note}" if note else ""
    logger.log(
        level,
        "[%s] %s → %s | %s | %s%s",
        operation,
        source,
        dest_str,
        size_str,
        result,
        note_str,
    )
