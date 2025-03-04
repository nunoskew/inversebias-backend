import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from inversebias.data.db import InverseBiasEngine, get_table, table_exists


@pytest.fixture
def mock_sqlalchemy_engine():
    """Mock the create_engine function and reset InverseBiasEngine singleton state"""
    # First, reset the singleton instance
    InverseBiasEngine._instance = None
    InverseBiasEngine._engine = None

    with patch("inversebias.data.db.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        yield mock_create_engine


def test_inverse_bias_engine_singleton(mock_sqlalchemy_engine):
    """Test that InverseBiasEngine is a singleton"""
    # Get two instances
    engine1 = InverseBiasEngine()
    engine2 = InverseBiasEngine()

    # Verify they are the same instance
    assert engine1 is engine2

    # Verify create_engine was called only once
    mock_sqlalchemy_engine.assert_called_once()
    # Check that first parameter contains sqlite
    assert "sqlite:///inverse_bias.db" in mock_sqlalchemy_engine.call_args[0][0]


@pytest.fixture
def mock_table_exists():
    with patch("inversebias.data.db.table_exists") as mock_exists:
        mock_exists.return_value = True
        yield mock_exists


@pytest.fixture
def mock_engine_connect():
    with patch.object(InverseBiasEngine, "engine") as mock_engine:
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        # Create mock DataFrame that would be returned by pd.read_sql
        mock_df = pd.DataFrame({"id": [1, 2], "name": ["Test1", "Test2"]})

        with patch("pandas.read_sql", return_value=mock_df) as mock_read_sql:
            yield {
                "engine": mock_engine,
                "connection": mock_connection,
                "read_sql": mock_read_sql,
                "expected_df": mock_df,
            }


def test_get_table(mock_table_exists, mock_engine_connect):
    """Test that get_table correctly fetches data from the database"""
    # Call get_table
    result = get_table("test_table")

    # Verify table_exists was called with the right table name
    mock_table_exists.assert_called_once_with("test_table")

    # Verify the SQL query was executed
    from sqlalchemy import text

    mock_engine_connect["read_sql"].assert_called_once()

    # Verify we got the expected DataFrame back
    pd.testing.assert_frame_equal(result, mock_engine_connect["expected_df"])
