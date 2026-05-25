"""
Tests for src.core.date_resolver and src.utils.date_utils.

Author: Nathan
"""

import pytest
from datetime import datetime
from collections import Counter

from src.utils.date_utils import majority_year_month, month_folder_name, format_duration, parse_exif_datetime


class TestParseExifDatetime:
    def test_standard_exif_format(self):
        dt = parse_exif_datetime("2023:06:15 14:30:00")
        assert dt == datetime(2023, 6, 15, 14, 30, 0)

    def test_dash_format(self):
        dt = parse_exif_datetime("2023-06-15 14:30:00")
        assert dt == datetime(2023, 6, 15, 14, 30, 0)

    def test_invalid_returns_none(self):
        assert parse_exif_datetime("not a date") is None

    def test_empty_returns_none(self):
        assert parse_exif_datetime("") is None


class TestMajorityYearMonth:
    def test_single_date(self):
        dates = [datetime(2022, 5, 10)]
        year, month, multi = majority_year_month(dates)
        assert year == 2022
        assert month == 5
        assert multi is False

    def test_majority_wins(self):
        dates = [
            datetime(2022, 3, 1), datetime(2022, 3, 2),
            datetime(2023, 6, 1),
        ]
        year, month, multi = majority_year_month(dates)
        assert year == 2022
        assert month == 3

    def test_tie_picks_oldest_year(self):
        dates = [datetime(2021, 1, 1), datetime(2022, 1, 1)]
        year, month, multi = majority_year_month(dates)
        assert year == 2021

    def test_multi_year_flag_more_than_two(self):
        dates = [datetime(2019, 1, 1), datetime(2020, 1, 1), datetime(2022, 1, 1)]
        _, _, multi = majority_year_month(dates)
        assert multi is True

    def test_two_years_not_multi(self):
        dates = [datetime(2021, 1, 1), datetime(2022, 1, 1)]
        _, _, multi = majority_year_month(dates)
        assert multi is False

    def test_empty_list(self):
        year, month, multi = majority_year_month([])
        assert year is None
        assert month is None
        assert multi is False


class TestMonthFolderName:
    def test_january(self):
        assert month_folder_name(1) == "01-January"

    def test_december(self):
        assert month_folder_name(12) == "12-December"


class TestFormatDuration:
    def test_seconds(self):
        assert format_duration(45) == "45s"

    def test_minutes(self):
        assert format_duration(90) == "1m 30s"

    def test_hours(self):
        assert format_duration(3661) == "1h 01m"
