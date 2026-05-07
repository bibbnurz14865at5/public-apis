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
REQUEST_TIMEOUT = 10  # seconds
MAX_WORKERS = 10
RETRY_COUNT = 2

# HTTP status codes considered valid
VALID_STATUS_CODES = set(range(200, 400))  # 2xx and 3xx


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
                return (name, url, False, f"HTTP {status}")
        except urllib.error.HTTPError as e:
            if e.code in VALID_STATUS_CODES:
                return (name, url, True, f"HTTP {e.code}")
            if attempt < retries:
                time.sleep(1)
                continue
            return (name, url, False, f"HTTP {e.code}")
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return (name, url, False, f"URLError: {e.reason}")
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return (name, url, False, f"Error: {str(e)}")

    return (name, url, False, "Max retries exceeded")


def validate_links(filepath: str = README_PATH) -> bool:
    """Validate all links found in the README file.

    Args:
        filepath: Path to the README.md file.

    Returns:
        True if all links are valid, False otherwise.
    """
    print(f"Extracting links from {filepath}...")
    links = extract_links_from_readme(filepath)

    if not links:
        print("No links found in README.")
        return True

    print(f"Found {len(links)} links. Validating...\n")

    failed = []
    passed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(check_url, name, url): (name, url)
            for name, url in links
        }
        for future in as_completed(futures):
            name, url, is_valid, status = future.result()
            if is_valid:
                passed += 1
                print(f"  ✓  {name}: {url} ({status})")
            else:
                failed.append((name, url, status))
                print(f"  ✗  {name}: {url} ({status})")

    print(f"\nResults: {passed} passed, {len(failed)} failed out of {len(links)} links.")

    if failed:
        print("\nFailed links:")
        for name, url, status in failed:
            print(f"  - {name}: {url} — {status}")
        return False

    return True


if __name__ == "__main__":
    success = validate_links()
    sys.exit(0 if success else 1)
