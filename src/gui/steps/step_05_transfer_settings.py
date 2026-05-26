"""
MediaMitigator — Step 5: Transfer Settings.

Lets the user configure empty-folder behavior, notifications, and
the optional Lightroom import report.

Author: Nathan
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QRadioButton, QCheckBox, QLineEdit, QFormLayout,
    QButtonGroup,
)
from PyQt6.QtCore import pyqtSignal

from src.gui.wizard_state import WizardState
from src.config.settings import save_settings

logger = logging.getLogger(__name__)


class TransferSettingsStep(QWidget):
    """Step 5 — transfer options panel.

    Signals:
        next_requested: User clicked Next.
        back_requested: User clicked Back.
    """

    next_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        """Initialise the settings step.

        Args:
            state: Shared wizard state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._state = state
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the step layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Transfer Settings")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # 1. Empty folder behavior
        empty_group = QGroupBox("Empty Source Folder Behavior (after successful transfer)")
        empty_layout = QVBoxLayout(empty_group)
        self._btn_group = QButtonGroup(self)
        self._radio_delete = QRadioButton("Delete empty folders")
        self._radio_flag = QRadioButton("Flag in report (leave folder)")
        self._radio_leave = QRadioButton("Leave alone")
        for btn in (self._radio_delete, self._radio_flag, self._radio_leave):
            empty_layout.addWidget(btn)
            self._btn_group.addButton(btn)
        self._radio_flag.setChecked(True)
        layout.addWidget(empty_group)

        # 2. Duplicate behavior info
        dup_group = QGroupBox("Duplicate Behavior")
        dup_layout = QVBoxLayout(dup_group)
        dup_layout.addWidget(QLabel(
            "True duplicates (same filename + same EXIF/creation date) will be "
            "moved to [destination]/_DUPLICATES_REVIEW/ for manual review."
        ))
        layout.addWidget(dup_group)

        # 3. Notifications
        notif_group = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notif_group)
        self._toast_cb = QCheckBox("Windows toast notifications")
        self._toast_cb.setChecked(True)
        notif_layout.addWidget(self._toast_cb)

        self._email_cb = QCheckBox("Email notifications (SMTP)")
        self._email_cb.stateChanged.connect(self._toggle_email)
        notif_layout.addWidget(self._email_cb)

        self._email_fields = QWidget()
        email_form = QFormLayout(self._email_fields)
        self._smtp_host = QLineEdit()
        self._smtp_port = QLineEdit("587")
        self._smtp_sender = QLineEdit()
        self._smtp_recipient = QLineEdit()
        self._smtp_password = QLineEdit()
        self._smtp_password.setEchoMode(QLineEdit.EchoMode.Password)
        email_form.addRow("SMTP Host:", self._smtp_host)
        email_form.addRow("Port:", self._smtp_port)
        email_form.addRow("Sender Email:", self._smtp_sender)
        email_form.addRow("Recipient Email:", self._smtp_recipient)
        email_form.addRow("Password:", self._smtp_password)
        self._email_fields.hide()
        notif_layout.addWidget(self._email_fields)
        layout.addWidget(notif_group)

        # 4. Lightroom report
        lr_group = QGroupBox("Lightroom Report")
        lr_layout = QVBoxLayout(lr_group)
        self._lr_cb = QCheckBox(
            "Generate folder list for Lightroom re-import "
            "(saves a .txt with all destination folder paths)"
        )
        lr_layout.addWidget(self._lr_cb)
        layout.addWidget(lr_group)

        # 5. Hardware profile summary
        self._hw_group = QGroupBox("Detected Hardware & Transfer Tuning")
        hw_layout = QVBoxLayout(self._hw_group)
        self._hw_label = QLabel("Hardware profile will appear after you select a destination in Step 3.")
        self._hw_label.setWordWrap(True)
        self._hw_label.setStyleSheet("color: #aaa; font-size: 12px;")
        hw_layout.addWidget(self._hw_label)
        layout.addWidget(self._hw_group)

        layout.addStretch()

        # Navigation
        nav = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("secondaryBtn")
        back_btn.setMinimumWidth(100)
        back_btn.clicked.connect(self.back_requested.emit)
        nav.addWidget(back_btn)
        nav.addStretch()
        next_btn = QPushButton("Next →")
        next_btn.setObjectName("primaryBtn")
        next_btn.setMinimumWidth(130)
        next_btn.clicked.connect(self._on_next)
        nav.addWidget(next_btn)
        layout.addLayout(nav)

    def _toggle_email(self, state: int) -> None:
        """Show or hide SMTP fields.

        Args:
            state: Checkbox state integer.
        """
        self._email_fields.setVisible(state != 0)

    def _on_next(self) -> None:
        """Persist settings and advance."""
        s = self._state.settings
        if self._radio_delete.isChecked():
            s["empty_folder_behavior"] = "delete"
        elif self._radio_leave.isChecked():
            s["empty_folder_behavior"] = "leave"
        else:
            s["empty_folder_behavior"] = "flag"

        s["toast_notifications"] = self._toast_cb.isChecked()
        s["email_notifications"] = self._email_cb.isChecked()
        s["email_host"] = self._smtp_host.text().strip()
        s["email_port"] = int(self._smtp_port.text().strip() or "587")
        s["email_sender"] = self._smtp_sender.text().strip()
        s["email_recipient"] = self._smtp_recipient.text().strip()
        s["email_password"] = self._smtp_password.text()
        s["lightroom_report"] = self._lr_cb.isChecked()
        save_settings(s)
        self.next_requested.emit()

    def _refresh_hardware_panel(self) -> None:
        """Update the hardware summary label from WizardState."""
        profile = self._state.hardware_profile
        if not profile:
            return

        def _badge(drive_type: str) -> str:
            colours = {"SSD": "#4caf50", "HDD": "#ff9800", "Unknown": "#888"}
            colour = colours.get(drive_type, "#888")
            return f"<span style='color:{colour}; font-weight:bold;'>{drive_type}</span>"

        admin_note = (
            "<span style='color:#4caf50'>✓ Admin — Defender exclusions will be applied</span>"
            if profile.is_admin else
            "<span style='color:#888'>⚠ Not admin — Defender exclusions unavailable</span>"
        )

        html = (
            f"Source drive: {_badge(profile.source_drive_type)}  &nbsp;|&nbsp;  "
            f"Destination drive: {_badge(profile.dest_drive_type)}<br>"
            f"Available RAM: <b>{profile.available_ram_gb:.1f} GB</b>  &nbsp;|&nbsp;  "
            f"CPU cores: <b>{profile.cpu_cores}</b><br>"
            f"Parallel workers: <b>{profile.optimal_workers}</b>  &nbsp;|&nbsp;  "
            f"Copy buffer: <b>{profile.optimal_buffer_mb} MB</b><br>"
            f"{admin_note}"
        )
        self._hw_label.setText(html)
        self._hw_label.setTextFormat(__import__('PyQt6.QtCore', fromlist=['Qt']).Qt.TextFormat.RichText)
        self._hw_label.setStyleSheet("font-size: 12px;")

    def refresh(self) -> None:
        """Restore saved settings when the step becomes visible."""
        self._refresh_hardware_panel()
        s = self._state.settings
        behavior = s.get("empty_folder_behavior", "flag")
        if behavior == "delete":
            self._radio_delete.setChecked(True)
        elif behavior == "leave":
            self._radio_leave.setChecked(True)
        else:
            self._radio_flag.setChecked(True)

        self._toast_cb.setChecked(s.get("toast_notifications", True))
        self._email_cb.setChecked(s.get("email_notifications", False))
        self._smtp_host.setText(s.get("email_host", ""))
        self._smtp_port.setText(str(s.get("email_port", 587)))
        self._smtp_sender.setText(s.get("email_sender", ""))
        self._smtp_recipient.setText(s.get("email_recipient", ""))
        self._smtp_password.setText(s.get("email_password", ""))
        self._lr_cb.setChecked(s.get("lightroom_report", False))
        self._toggle_email(self._email_cb.checkState().value)
