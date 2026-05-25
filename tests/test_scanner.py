"""
Tests for src.core.scanner helpers.

Author: Nathan
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.scanner import enumerate_drives
from src.models.scan_result import DriveInfo


class TestEnumerateDrives:
    def test_returns_list(self):
        """enumerate_drives should always return a list."""
        result = enumerate_drives()
        assert isinstance(result, list)

    def test_cdrom_excluded(self):
        """CD-ROM drives must be filtered out."""
        mock_partition = MagicMock()
        mock_partition.opts = "cdrom"
        mock_partition.fstype = "udf"
        mock_partition.mountpoint = "D:\\"
        mock_partition.device = "D:\\"

        mock_usage = MagicMock()
        mock_usage.total = 1024 ** 3
        mock_usage.free = 512 * 1024 ** 2

        with patch("psutil.disk_partitions", return_value=[mock_partition]):
            with patch("psutil.disk_usage", return_value=mock_usage):
                result = enumerate_drives()
        assert result == []

    def test_normal_drive_included(self):
        """A normal fixed drive should be returned."""
        mock_partition = MagicMock()
        mock_partition.opts = "fixed"
        mock_partition.fstype = "NTFS"
        mock_partition.mountpoint = "E:\\"
        mock_partition.device = "E:\\"

        mock_usage = MagicMock()
        mock_usage.total = 2 * 1024 ** 3
        mock_usage.free = 1024 ** 3

        with patch("psutil.disk_partitions", return_value=[mock_partition]):
            with patch("psutil.disk_usage", return_value=mock_usage):
                result = enumerate_drives()
        assert len(result) == 1
        assert result[0].letter == "E"


class TestDriveInfo:
    def test_usage_percent(self):
        di = DriveInfo("D", "Test", 100, 25)
        assert di.usage_percent == pytest.approx(75.0)

    def test_root_path(self):
        di = DriveInfo("F", "Media", 100, 50)
        assert di.root_path == Path("F:\\")

    def test_zero_total_bytes(self):
        di = DriveInfo("G", "", 0, 0)
        assert di.usage_percent == 0.0
