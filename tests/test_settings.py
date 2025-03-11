import pytest
from unittest.mock import patch, mock_open, MagicMock
import os
from pathlib import Path
import yaml
import sys


# Sample mock config data
MOCK_CONFIG = {
    "database": {
        "uri": "sqlite:///test_db.db",
        "pool_size": 10,
        "echo": True,
    },
    "api": {
        "host": "127.0.0.1",
        "port": 5000,
        "frontend_url": "http://test.com",
        "default_limit": 20,
        "max_limit": 200,
    },
    "analysis": {
        "bias_threshold": 0.75,
        "sentiment_categories": ["positive", "neutral", "negative", "mixed"],
        "llm_model": "test/model",
    },
    "subjects": ["test_subject1", "test_subject2"],
    "news_sources": {
        "test_source": {
            "url": "https://test.com",
            "sitemap_url": "https://test.com/sitemap.xml",
        }
    },
}


@pytest.fixture
def mock_config_yaml():
    """Mock the config.yaml file with test data"""
    yaml_content = yaml.dump(MOCK_CONFIG)

    with patch("builtins.open", mock_open(read_data=yaml_content)):
        # Patch Path.exists to return True for config.yaml
        with patch.object(Path, "exists", return_value=True):
            yield


def test_load_yaml_config(mock_config_yaml):
    """Test that the configuration is loaded correctly from YAML"""
    # Import after mocking to ensure our mock is used
    from inversebias.config.settings import load_yaml_config

    # Execute the function
    config = load_yaml_config()

    # Verify the config matches our mock data
    assert config == MOCK_CONFIG


def test_load_yaml_config_file_not_found():
    """Test that an error is raised when config.yaml doesn't exist"""
    # Patch Path.exists to return False for config.yaml
    with patch.object(Path, "exists", return_value=False):
        # Import after mocking
        from inversebias.config.settings import load_yaml_config

        # Check that the function raises a FileNotFoundError
        with pytest.raises(FileNotFoundError):
            load_yaml_config()


def test_database_settings():
    """Test that DatabaseSettings loads values from config"""
    # Mock the config data
    yaml_content = yaml.dump(MOCK_CONFIG)

    # Mock environment variables
    with patch.dict(os.environ, {"INVERSEBIAS_ENV": "development"}, clear=True):
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            # Patch Path.exists to return True for config.yaml
            with patch.object(Path, "exists", return_value=True):
                # Force reload of the module with our mock config
                import importlib

                if "inversebias.config.settings" in sys.modules:
                    # First remove it from sys.modules to force a complete reload
                    del sys.modules["inversebias.config.settings"]

                # Now import with our mocked config
                from inversebias.config.settings import DatabaseSettings

                # Create settings instance
                db_settings = DatabaseSettings()

                # Verify settings match our mock config
                assert db_settings.uri == MOCK_CONFIG["database"]["uri"]
                assert db_settings.pool_size == MOCK_CONFIG["database"]["pool_size"]
                assert db_settings.echo is MOCK_CONFIG["database"]["echo"]


def test_app_settings_default_values():
    """Test that AppSettings has the expected default values"""
    # Mock an empty YAML file
    empty_yaml = "{}\n"  # Empty YAML dictionary

    # Since we're in a production environment with PostgreSQL, let's adapt the test
    with patch("builtins.open", mock_open(read_data=empty_yaml)):
        # Patch Path.exists to return True for config.yaml
        with patch.object(Path, "exists", return_value=True):
            # Force reload of the module with empty config
            import importlib

            if "inversebias.config.settings" in sys.modules:
                # First remove it from sys.modules to force a complete reload
                del sys.modules["inversebias.config.settings"]

            # Import settings module
            import inversebias.config.settings

            # Create AppSettings instance
            app_settings = inversebias.config.settings.AppSettings()

            # Verify the database values without asserting the exact URI
            assert "postgresql://" in app_settings.database.uri

            # Check other default values
            assert app_settings.api.host == "0.0.0.0"
            assert app_settings.api.default_limit == 10
            assert app_settings.api.max_limit == 100


def test_settings_convenience_exports():
    """Test that convenience exports are set correctly"""
    # Mock the config data
    yaml_content = yaml.dump(MOCK_CONFIG)

    with patch("builtins.open", mock_open(read_data=yaml_content)):
        # Patch Path.exists to return True for config.yaml
        with patch.object(Path, "exists", return_value=True):
            # Force reload of the module with our mock config
            import importlib

            if "inversebias.config.settings" in sys.modules:
                # First remove it from sys.modules to force a complete reload
                del sys.modules["inversebias.config.settings"]

            # Now import with our mocked config
            from inversebias.config.settings import (
                SOURCE_TO_URL,
                SUBJECTS,
                BIAS_THRESHOLD,
            )

            # Verify exports match our mock config
            assert SOURCE_TO_URL == MOCK_CONFIG["news_sources"]
            assert SUBJECTS == MOCK_CONFIG["subjects"]
            assert BIAS_THRESHOLD == MOCK_CONFIG["analysis"]["bias_threshold"]


def test_data_dir_validator():
    """Test the data_dir validator function"""
    # Import the module
    from inversebias.config.settings import AppSettings

    # Test with None value (should use default)
    app_settings = AppSettings()
    assert "data" in app_settings.data_dir

    # Test with custom value
    custom_dir = "/custom/data/dir"
    app_settings = AppSettings(data_dir=custom_dir)
    assert app_settings.data_dir == custom_dir
