import pytest
import os
from unittest.mock import patch, MagicMock
import pandas as pd

# Patch environment variable and ChatGPTAPI before importing from inversebias modules
with patch.dict(os.environ, {"CHATGPT_APIKEY": "mock_api_key"}):
    with patch("inversebias.ml.ChatGPTAPI") as mock_chatgpt:
        mock_instance = MagicMock()
        mock_instance.ask.return_value = "Mock ChatGPT response"
        mock_chatgpt.return_value = mock_instance
        from inversebias.pipeline import today_pipeline


@pytest.fixture
def mock_pipeline_components():
    with patch("inversebias.pipeline.build_today") as mock_build_today, patch(
        "inversebias.pipeline.filter_subjects_of_interest"
    ) as mock_filter, patch(
        "inversebias.pipeline.infer_sentiment"
    ) as mock_infer, patch(
        "inversebias.pipeline.build_inverse_bias"
    ) as mock_build_bias:

        # Set up return values for each step
        title_df = pd.DataFrame(
            {"url": ["https://example.com/article1", "https://example.com/article2"]}
        )
        subject_df = pd.DataFrame(
            {"url": ["https://example.com/article1"], "subject": ["politics"]}
        )
        sentiment_df = pd.DataFrame(
            {
                "url": ["https://example.com/article1"],
                "subject": ["politics"],
                "sentiment": ["positive"],
            }
        )
        bias_df = pd.DataFrame(
            {
                "url": ["https://example.com/article1"],
                "subject": ["politics"],
                "sentiment": ["positive"],
                "bias": ["left"],
            }
        )

        mock_build_today.return_value = title_df
        mock_filter.return_value = subject_df
        mock_infer.return_value = sentiment_df
        mock_build_bias.return_value = bias_df

        yield {
            "build_today": mock_build_today,
            "filter_subjects": mock_filter,
            "infer_sentiment": mock_infer,
            "build_bias": mock_build_bias,
            "expected_result": bias_df,
        }


def test_today_pipeline(mock_pipeline_components):
    """Test that today_pipeline runs all steps in the correct order"""
    # Run the pipeline without uploading
    result = today_pipeline(upload=False, verbose=True)

    # Verify each step was called with correct parameters
    mock_pipeline_components["build_today"].assert_called_once_with(
        upload=False, verbose=True
    )

    mock_pipeline_components["filter_subjects"].assert_called_once()
    title_df_arg = mock_pipeline_components["filter_subjects"].call_args[0][0]
    assert isinstance(title_df_arg, pd.DataFrame)

    mock_pipeline_components["infer_sentiment"].assert_called_once()
    subject_df_arg = mock_pipeline_components["infer_sentiment"].call_args[0][0]
    assert isinstance(subject_df_arg, pd.DataFrame)

    mock_pipeline_components["build_bias"].assert_called_once()
    sentiment_df_arg = mock_pipeline_components["build_bias"].call_args[0][0]
    assert isinstance(sentiment_df_arg, pd.DataFrame)

    # Verify the result is the expected DataFrame
    pd.testing.assert_frame_equal(result, mock_pipeline_components["expected_result"])
