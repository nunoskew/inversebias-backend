import pytest
import os
from unittest.mock import patch, MagicMock

# Patch environment variable and ChatGPTAPI before importing from inversebias.ml
with patch.dict(os.environ, {"CHATGPT_APIKEY": "mock_api_key"}):
    with patch("inversebias.ml.ChatGPTAPI") as mock_chatgpt:
        mock_instance = MagicMock()
        mock_instance.ask.return_value = "Mock ChatGPT response"
        mock_chatgpt.return_value = mock_instance
        from inversebias.ml import ask_llm, LLAMA_API


@pytest.fixture
def mock_llama_api():
    # Directly patch the ask method of the LLAMA_API instance
    original_ask = LLAMA_API.ask
    LLAMA_API.ask = MagicMock(return_value="This is a mock response")
    yield LLAMA_API
    # Restore the original method after the test
    LLAMA_API.ask = original_ask


def test_ask_llm(mock_llama_api):
    """Test that ask_llm function properly calls the LLM API"""
    # Test with default API
    result = ask_llm("What is the meaning of life?")
    assert result == "This is a mock response"
    mock_llama_api.ask.assert_called_once_with("What is the meaning of life?")

    # Test with custom API
    custom_api = MagicMock()
    custom_api.ask.return_value = "Custom response"
    result = ask_llm("What is your name?", llm_api=custom_api)
    assert result == "Custom response"
    custom_api.ask.assert_called_once_with("What is your name?")
