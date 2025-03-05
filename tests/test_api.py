import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
from inversebias.api import app


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def mock_db_connection():
    # Create a mock dataframe that the SQL query would return
    articles = [
        {
            "source": "CNN",
            "subject": "politics",
            "url": "https://cnn.com/article1",
            "title": "Article about politics",
            "publication_date": "2023-01-01",
            "sentiment": "positive",
            "explanation": "Positive explanation",
            "bias": "left",
            "num_negative": 2,
            "num_positive": 8,
        },
        {
            "source": "Fox News",
            "subject": "economy",
            "url": "https://foxnews.com/article2",
            "title": "Article about economy",
            "publication_date": "2023-01-02",
            "sentiment": "negative",
            "explanation": "Negative explanation",
            "bias": "right",
            "num_negative": 8,
            "num_positive": 2,
        },
    ]

    # Mock the entire database connection and query execution
    with patch("inversebias.api.InverseBiasEngine") as mock_engine_class:
        # Create mock engine instance
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        # Mock the engine property
        mock_db_engine = MagicMock()
        type(mock_engine).engine = mock_db_engine

        # Mock connection context manager
        mock_conn = MagicMock()
        mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock execute().mappings().all() to return our test data
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_conn.execute.return_value = mock_result
        mock_result.mappings.return_value = mock_mappings
        mock_mappings.all.return_value = articles

        yield


def test_get_articles(test_client, mock_db_connection):
    """Test the GET /articles endpoint"""
    # Test the default parameters
    response = test_client.get("/articles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Verify the structure of returned data
    assert data[0]["source"] == "CNN"
    assert data[0]["subject"] == "politics"
    assert data[0]["url"] == "https://cnn.com/article1"
    assert data[0]["title"] == "Article about politics"
    assert data[0]["sentiment"] == "positive"
    assert data[0]["num_negative"] == 2
    assert data[0]["num_positive"] == 8

    # Test with a filter parameter
    response = test_client.get("/articles?source=CNN")
    assert response.status_code == 200
