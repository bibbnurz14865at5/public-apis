#!/usr/bin/env python3
"""Tests for scripts/validate_entries.py"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from validate_entries import parse_table_rows, validate_row, validate_readme


SAMPLE_CONTENT = """
## Category

| API | Description | Auth | HTTPS | CORS |
|---|---|---|---|---|
| CoolAPI | A cool API | apiKey | Yes | No |
| FreeAPI | A free API |  | Yes | Yes |
| OAuthAPI | OAuth based | OAuth | No | Unknown |
"""

INVALID_CONTENT = """
## Category

| API | Description | Auth | HTTPS | CORS |
|---|---|---|---|---|
| BadAPI | Missing fields | badAuth | Maybe | Sometimes |
|  | No name here | apiKey | Yes | No |
"""


def test_parse_table_rows_returns_data_rows():
    rows = parse_table_rows(SAMPLE_CONTENT)
    assert len(rows) == 3


def test_parse_table_rows_skips_header_and_separator():
    rows = parse_table_rows(SAMPLE_CONTENT)
    api_names = [cells[0] for _, cells in rows]
    assert "API" not in api_names
    assert "---" not in api_names


def test_validate_row_valid_entry():
    cells = ["CoolAPI", "A cool API", "apiKey", "Yes", "No"]
    errors = validate_row(1, cells)
    assert errors == []


def test_validate_row_empty_auth_is_valid():
    cells = ["FreeAPI", "A free API", "", "Yes", "Yes"]
    errors = validate_row(1, cells)
    assert errors == []


def test_validate_row_invalid_auth():
    cells = ["BadAPI", "Some API", "badAuth", "Yes", "No"]
    errors = validate_row(5, cells)
    assert any("Auth" in e for e in errors)


def test_validate_row_invalid_https():
    cells = ["BadAPI", "Some API", "apiKey", "Maybe", "No"]
    errors = validate_row(5, cells)
    assert any("HTTPS" in e for e in errors)


def test_validate_row_invalid_cors():
    cells = ["BadAPI", "Some API", "apiKey", "Yes", "Sometimes"]
    errors = validate_row(5, cells)
    assert any("CORS" in e for e in errors)


def test_validate_row_empty_api_name():
    cells = ["", "Some description", "apiKey", "Yes", "No"]
    errors = validate_row(5, cells)
    assert any("API name" in e for e in errors)


def test_validate_readme_missing_file():
    result = validate_readme("nonexistent_file.md")
    assert result == 1


def test_validate_readme_with_valid_content(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(SAMPLE_CONTENT, encoding="utf-8")
    result = validate_readme(str(readme))
    assert result == 0


def test_validate_readme_with_invalid_content(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(INVALID_CONTENT, encoding="utf-8")
    result = validate_readme(str(readme))
    assert result > 0


# NOTE: Added to verify that both invalid rows in INVALID_CONTENT are caught,
# not just the first one. Useful sanity check when modifying validate_readme.
def test_validate_readme_invalid_content_catches_multiple_errors(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(INVALID_CONTENT, encoding="utf-8")
    # INVALID_CONTENT has two bad rows: one with invalid Auth/HTTPS/CORS values
    # and one with an empty API name. We expect at least 2 distinct errors total.
    # This ensures validate_readme doesn't short-circuit after the first failure.
    errors_found = validate_readme(str(readme))
    assert errors_found >= 2
