"""
Tests for src.core.transfer_engine helpers and logic.

Author: Nathan
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.file_utils import next_available_path, human_readable_size, safe_copy, safe_delete


class TestNextAvailablePath:
    def test_no_conflict_returns_original(self, tmp_path):
        p = tmp_path / "photo.jpg"
        assert next_available_path(p) == p

    def test_conflict_increments_suffix(self, tmp_path):
        p = tmp_path / "photo.jpg"
        p.write_bytes(b"x")
        result = next_available_path(p)
        assert result == tmp_path / "photo_2.jpg"

    def test_multiple_conflicts(self, tmp_path):
        for name in ("photo.jpg", "photo_2.jpg", "photo_3.jpg"):
            (tmp_path / name).write_bytes(b"x")
        result = next_available_path(tmp_path / "photo.jpg")
        assert result == tmp_path / "photo_4.jpg"


class TestHumanReadableSize:
    def test_bytes(self):
        assert "B" in human_readable_size(500)

    def test_kilobytes(self):
        assert "KB" in human_readable_size(2048)

    def test_megabytes(self):
        assert "MB" in human_readable_size(5 * 1024 * 1024)

    def test_gigabytes(self):
        assert "GB" in human_readable_size(2 * 1024 ** 3)


class TestSafeCopy:
    def test_successful_copy(self, tmp_path):
        src = tmp_path / "source.jpg"
        src.write_bytes(b"hello world")
        dst = tmp_path / "sub" / "dest.jpg"
        result = safe_copy(src, dst)
        assert result is True
        assert dst.exists()
        assert dst.read_bytes() == b"hello world"

    def test_missing_source_returns_false(self, tmp_path):
        src = tmp_path / "nonexistent.jpg"
        dst = tmp_path / "dest.jpg"
        result = safe_copy(src, dst)
        assert result is False


class TestSafeDelete:
    def test_deletes_existing_file(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"x")
        result = safe_delete(f)
        assert result is True
        assert not f.exists()

    def test_missing_file_returns_true(self, tmp_path):
        f = tmp_path / "missing.txt"
        result = safe_delete(f)
        assert result is True
