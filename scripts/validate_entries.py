#!/usr/bin/env python3
"""Validate entries in the public APIs README.md file."""

import re
import sys
from typing import List, Tuple

README_PATH = "README.md"

# Expected table header format
TABLE_HEADER = "| API | Description | Auth | HTTPS | CORS |"
TABLE_SEPARATOR = "|---|---|---|---|---|"

# Note: "No" is listed here as a valid auth value but in practice entries use
# an empty string to indicate no auth. "No" appears to be a legacy value.
VALID_AUTH_VALUES = {"", "apiKey", "OAuth", "X-Mashape-Key", "No"}
VALID_HTTPS_VALUES = {"Yes", "No"}
VALID_CORS_VALUES = {"Yes", "No", "Unknown"}

# Minimum description length threshold. Raised from 10 to 15 because I kept
# seeing entries like "An API for X" (11 chars) that were still too vague.
MIN_DESCRIPTION_LENGTH = 15


def parse_table_rows(content: str) -> List[Tuple[int, List[str]]]:
    """Extract table rows from README content with line numbers."""
    rows = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(cells) == 5 and cells[0] not in ("", "API", "---"):
                rows.append((line_num, cells))
    return rows


def validate_row(line_num: int, cells: List[str]) -> List[str]:
    """Validate a single table row and return list of error messages."""
    errors = []
    api_name, description, auth, https, cors = cells

    if not api_name:
        errors.append(f"Line {line_num}: API name is empty.")

    if not description:
        errors.append(f"Line {line_num}: Description is empty for '{api_name}'.")

    # Check description doesn't end with a period (style consistency)
    if description.endswith("."):
        errors.append(
            f"Line {line_num}: Description for '{api_name}' should not end with a period."
        )

    # Also flag descriptions that end with an exclamation mark or question mark
    # since those feel out of place in a reference table too
    if description.endswith("!") or description.endswith("?"):
        errors.append(
            f"Line {line_num}: Description for '{api_name}' should not end with punctuation."
        )

    # Flag descriptions that are suspiciously short -- likely placeholder or incomplete.
    # I kept seeing entries like "An API" slip through, so adding a minimum length check.
    if description and len(description) < MIN_DESCRIPTION_LENGTH:
        errors.append(
            f"Line {line_num}: Description for '{api_name}' seems too short "
            f"(< {MIN_DESCRIPTION_LENGTH} chars)."
        )

    # Strip markdown link from auth if present
    auth_clean = re.sub(r"\[.*?\]\(.*?\)", "", auth).strip()
    if auth_clean not in VALID_AUTH_VALUES:
        errors.append(
            f"Line {line_num}: Invalid Auth value '{auth}' for '{api_name}'. "
            f"Expected one of: {VALID_AUTH_VALUES}"
        )

    if https not in VALID_HTTPS_VALUES:
        errors.append(
            f"Line {line_num}: Invalid HTTPS value '{https}' for '{api_name}'. "
            f"Expected one of: {VALID_HTTPS_VALUES}"
        )

    if cors not in VALID_CORS_VALUES:
        errors.append(
