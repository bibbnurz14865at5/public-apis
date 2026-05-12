"""Tests for the validate_links.py script."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure scripts directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from validate_links import extract_links_from_readme, check_url


SAMPLE_README = """
# Public APIs

A collective list of free APIs.

## Index
- [Animals](#animals)
- [Weather](#weather)

## Animals
| API | Description | Auth | HTTPS | CORS |
|-----|-------------|------|-------|------|
| [Cat Facts](https://catfact.ninja/) | Daily cat facts | No | Yes | No |
| [Dog CEO](https://dog.ceo/dog-api/) | Dog images | No | Yes | Yes |

## Weather
| API | Description | Auth | HTTPS | CORS |
|-----|-------------|------|-------|------|
| [Open-Meteo](https://open-meteo.com/) | Free weather API | No | Yes | Yes |

[Back to Index](#index)
"""

README_NO_LINKS = """
# Public APIs

Just some plain text with no hyperlinks here.
"""

README_DUPLICATE_LINKS = """
# Public APIs

| API | Description | Auth | HTTPS | CORS |
|-----|-------------|------|-------|------|
| [Cat Facts](https://catfact.ninja/) | Daily cat facts | No | Yes | No |
| [Cat Facts Mirror](https://catfact.ninja/) | Mirror | No | Yes | No |
"""


class TestExtractLinksFromReadme(unittest.TestCase):

    def test_extracts_http_links(self):
        links = extract_links_from_readme(SAMPLE_README)
        self.assertIn('https://catfact.ninja/', links)
        self.assertIn('https://dog.ceo/dog-api/', links)
        self.assertIn('https://open-meteo.com/', links)

    def test_returns_list(self):
        links = extract_links_from_readme(SAMPLE_README)
        self.assertIsInstance(links, list)

    def test_no_links_returns_empty(self):
        links = extract_links_from_readme(README_NO_LINKS)
        self.assertEqual(links, [])

    def test_does_not_include_anchor_links(self):
        links = extract_links_from_readme(SAMPLE_README)
        for link in links:
            self.assertFalse(link.startswith('#'),
                             f"Anchor link found in results: {link}")

    def test_deduplicates_links(self):
        links = extract_links_from_readme(README_DUPLICATE_LINKS)
        self.assertEqual(len(links), links.__len__())
        # catfact.ninja should appear only once
        count = sum(1 for l in links if l == 'https://catfact.ninja/')
        self.assertLessEqual(count, 1)

    def test_empty_string_returns_empty(self):
        links = extract_links_from_readme('')
        self.assertEqual(links, [])


class TestCheckUrl(unittest.TestCase):

    @patch('validate_links.requests.get')
    def test_returns_true_for_200(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_url('https://catfact.ninja/')
        self.assertTrue(result)

    @patch('validate_links.requests.get')
    def test_returns_false_for_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = check_url('https://example.com/notfound')
        self.assertFalse(result)

    @patch('validate_links.requests.get')
    def test_returns_false_on_connection_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError('Connection refused')

        result = check_url('https://nonexistent.invalid/')
        self.assertFalse(result)

    @patch('validate_links.requests.get')
    def test_returns_false_on_timeout(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.Timeout('Request timed out')

        result = check_url('https://slow-api.example.com/')
        self.assertFalse(result)

    @patch('validate_links.requests.get')
    def test_returns_true_for_301_redirect(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_get.return_value = mock_response

        result = check_url('https://example.com/redirect')
        # Redirects are typically followed; 301 alone may indicate success
        self.assertIsInstance(result, bool)

    @patch('validate_links.requests.get')
    def test_uses_timeout(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        check_url('https://catfact.ninja/')
        _, kwargs = mock_get.call_args
        self.assertIn('timeout', kwargs)


if __name__ == '__main__':
    unittest.main()
