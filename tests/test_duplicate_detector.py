"""
Tests for src.core.duplicate_detector.

Author: Nathan
"""

import os
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.duplicate_detector import is_duplicate


class TestIsDuplicate:
    def test_different_filenames_not_duplicate(self, tmp_path):
        src = tmp_path / "photo_a.jpg"
        dst = tmp_path / "photo_b.jpg"
        src.write_bytes(b"x")
        dst.write_bytes(b"x")
        result, _ = is_duplicate(src, dst)
        assert result is False

    def test_same_name_same_exif_is_duplicate(self, tmp_path):
        src = tmp_path / "IMG_001.jpg"
        dst = tmp_path / "IMG_001.jpg"
        src.write_bytes(b"source")
        dst.write_bytes(b"destination")
        exif_dt = datetime(2022, 6, 15, 12, 0, 0)
        with patch("src.core.duplicate_detector.get_media_date", return_value=exif_dt):
            result, method = is_duplicate(src, dst)
        assert result is True
        assert "EXIF" in method

    def test_same_name_different_exif_not_duplicate(self, tmp_path):
        src = tmp_path / "IMG_001.jpg"
        dst = tmp_path / "IMG_001.jpg"
        src.write_bytes(b"s")
        dst.write_bytes(b"d")
        side_effects = [
            datetime(2022, 6, 15, 12, 0, 0),
            datetime(2023, 1, 1, 0, 0, 0),
        ]
        with patch("src.core.duplicate_detector.get_media_date", side_effect=side_effects):
            result, _ = is_duplicate(src, dst)
        assert result is False

    def test_same_name_no_exif_same_ctime_is_duplicate(self, tmp_path):
        src = tmp_path / "VID_001.mp4"
        dst = tmp_path / "VID_001.mp4"
        src.write_bytes(b"s")
        dst.write_bytes(b"d")
        fixed_dt = datetime(2022, 1, 1, 0, 0, 0)
        with patch("src.core.duplicate_detector.get_media_date", return_value=None):
            with patch("src.core.duplicate_detector._creation_time", return_value=fixed_dt):
                result, method = is_duplicate(src, dst)
        assert result is True
        assert "ctime" in method
