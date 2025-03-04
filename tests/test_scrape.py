import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from inversebias.scrape import standard_scrape, StandardScrapePayload


@pytest.fixture
def mock_scrape():
    with patch("inversebias.scrape.scrape") as mock_scrape_func:
        mock_scrape_func.return_value = {
            "content": "Mocked HTML content",
            "markdown": "# Mocked Markdown\nThis is some mocked markdown content",
        }
        yield mock_scrape_func


def test_standard_scrape(mock_scrape):
    """Test that standard_scrape function properly calls the scraping service"""
    url = "https://example.com/article"
    formats = ["html", "markdown"]

    result = standard_scrape(url, formats=formats)

    # Verify the scrape function was called with correct parameters
    expected_payload = StandardScrapePayload(
        url=url,
        formats=formats,
        onlyMainContent=True,
        excludeTags=["script", "style", ".ad", "#footer"],
        includeTags=[],
    )

    mock_scrape.assert_called_once()
    call_args = mock_scrape.call_args[1]
    assert "scrape_payload" in call_args

    # Verify the result contains the expected content
    assert result.get("content") == "Mocked HTML content"
    assert (
        result.get("markdown")
        == "# Mocked Markdown\nThis is some mocked markdown content"
    )
