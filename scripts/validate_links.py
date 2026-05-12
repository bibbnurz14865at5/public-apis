#!/usr/bin/env python3
"""Script to validate that API links in README.md are reachable.

This script parses the README.md file, extracts all API links from the
table entries, and checks each one with an HTTP HEAD request to verify
the URL is accessible. Results are reported with pass/fail status.
"""

import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

README_PATH = "README.md"
REQUEST_TIMEOUT = 15  # seconds; increased from 10 to reduce false negatives on slow APIs
MAX_WORKERS = 10
RETRY_COUNT = 3  # bumped from 2 to 3 since some APIs are flaky on first attempt

# HTTP status codes considered valid
VALID_STATUS_CODES = set(range(200, 400))  # 2xx and 3xx

# Additional status codes to treat as valid beyond 2xx/3xx.
# 401 and 403 mean the server is up but requires auth — the link itself is fine.
# 405 means HEAD method not allowed but server is reachable.
# 429 means rate limited — server is up, just throttling us.
# 503 added personally — some APIs return 503 under load but are still "up".
# 999 added because LinkedIn returns 999 to block bots; the site is still reachable.
# 406 added because some APIs reject HEAD requests with "Not Acceptable" but are reachable.
EXTRA_VALID_STATUS_CODES = {401, 403, 405, 406, 429, 503, 999}


def extract_links_from_readme(filepath: str) -> List[Tuple[str, str]]:
    """Extract all hyperlinks from table rows in the README.

    Args:
        filepath: Path to the README.md file.

    Returns:
        A list of (api_name, url) tuples found in table entries.
    """
    links = []
    # Match markdown links like [Name](https://example.com)
    link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            # Only process table rows (lines starting with |)
            if not line.strip().startswith("|"):
                continue
            # Skip separator rows
            if re.match(r'^[\s|:-]+$', line.strip()):
                continue
            matches = link_pattern.findall(line)
            for name, url in matches:
                links.append((name, url))

    return links


def check_url(name: str, url: str, retries: int = RETRY_COUNT) -> Tuple[str, str, bool, str]:
    """Check if a URL is reachable via HTTP HEAD request.

    Args:
        name: Display name of the API.
        url: The URL to check.
        retries: Number of retry attempts on failure.

    Returns:
        A tuple of (name, url, is_valid, status_message).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; public-apis-validator/1.0)"
    }

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, method="HEAD", headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                status = response.status
                if status in VALID_STATUS_CODES:
                    return (name, url, True, f"HTTP {status}")
      