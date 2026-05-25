"""
Tests for src.core.analyzer.

Author: Nathan
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.core.analyzer import resolve_destination, build_transfer_plan
from src.models.folder_node import FolderNode, FolderStatus
from src.models.scan_result import ScanResult


class TestResolveDestination:
    def test_basic_path_structure(self):
        node = FolderNode(
            path=Path("/source/Yellowstone Trip"),
            majority_year=2023,
            majority_month=8,
        )
        dest = resolve_destination(node, Path("D:/Photos"))
        assert dest == Path("D:/Photos/2023/08-August/Yellowstone Trip")

    def test_missing_year_defaults_to_zero(self):
        node = FolderNode(path=Path("/source/Unknown"))
        dest = resolve_destination(node, Path("D:/Photos"))
        assert dest.parts[-3] == "0"

    def test_folder_name_preserved(self):
        node = FolderNode(
            path=Path("/some/deep/path/My Vacation"),
            majority_year=2021,
            majority_month=7,
        )
        dest = resolve_destination(node, Path("E:/Backup"))
        assert dest.name == "My Vacation"


class TestBuildTransferPlan:
    def test_excludes_unchecked_folders(self, tmp_path):
        node_checked = FolderNode(path=tmp_path / "checked", is_checked=True)
        node_checked.path.mkdir()
        node_unchecked = FolderNode(path=tmp_path / "unchecked", is_checked=True)
        node_unchecked.path.mkdir()

        scan = ScanResult(folder_nodes=[node_checked, node_unchecked])
        checked_paths = {node_checked.path}

        with patch("src.core.analyzer.resolve_folder_dates", return_value=(2022, 5, False)):
            with patch("src.core.analyzer.run_speed_test", return_value=100.0):
                plan = build_transfer_plan(scan, tmp_path / "dest", checked_paths)

        assert len(plan.folder_nodes) == 1
        assert plan.folder_nodes[0].path == node_checked.path
        assert node_unchecked.status == FolderStatus.EXCLUDED

    def test_plan_totals(self, tmp_path):
        n1 = FolderNode(path=tmp_path / "a", file_count=10, total_size_bytes=1000)
        n1.path.mkdir()
        n2 = FolderNode(path=tmp_path / "b", file_count=5, total_size_bytes=500)
        n2.path.mkdir()
        scan = ScanResult(folder_nodes=[n1, n2])

        with patch("src.core.analyzer.resolve_folder_dates", return_value=(2023, 3, False)):
            with patch("src.core.analyzer.run_speed_test", return_value=50.0):
                plan = build_transfer_plan(scan, tmp_path / "dest")

        assert plan.total_files == 15
        assert plan.total_size_bytes == 1500
