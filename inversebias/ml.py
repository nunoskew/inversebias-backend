import numpy as np
import ollama
import pandas as pd
import re
import requests
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from pandera.typing import DataFrame
from pandera import check_types
from inversebias.data.db import (
    get_table,
    sql_replace_df,
    table_upload,
    upload_to_table,
)
from inversebias.data.utils import empty_dataframe_from_model, groupby_mode
from inversebias.data.df_schema import (
    BiasInput,
    InverseBiasOutput,
    SentimentDataInput,
    SitemapScrape,
)
from inversebias.config import settings
from inversebias.data.utils import  SUBJECTS

# Load environment variables from .env file
load_dotenv()

from abc import ABC, abstractmethod


class LlmAPI(ABC):
    """
    Abstract base class for LLM APIs.
    """

    def __init__(self, url: str, model: str):
        """
        Initialize the LLM API.
        """
        self.url: str = url
        self.model: str = model
        self.apikey: str = None
        self.headers: dict = {"Content-Type": "application/json"}
        self.payload: dict = {}

    @abstractmethod
    def ask(self, question: str) -> str:
        """
        Ask the LLM API a question.
        """
        raise NotImplementedError("Subclasses must implement this method")


class ChatGPTAPI(LlmAPI):
    def __init__(self):
        super().__init__(
            url="https://api.openai.com/v1/chat/completions",
            model="gpt-4o-mini",
        )
        self.apikey = os.environ.get("CHATGPT_APIKEY")
        if not self.apikey:
            raise ValueError("CHATGPT_APIKEY environment variable not set")
        self.headers["Authorization"] = f"Bearer {self.apikey}"
        self.payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": None}],
            "stream": False,
        }

    def ask(self, question: str) -> str:
        self.payload["messages"][0]["content"] = question
        response = requests.post(self.url, json=self.payload, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"ChatGPT API error: {response.text}")
        return response.json()["choices"][0]["message"]["content"]


class LLamaAPI(LlmAPI):
    def __init__(self):
        super().__init__(
            url="http://localhost:11434/api/chat",
            model="llama3.1",
        )
        self.payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": None}],
            "stream": False,
        }

    def ask(self, question: str) -> str:
        self.payload["messages"][0]["content"] = question
        response = requests.post(self.url, json=self.payload, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Llama API error: {response.text}")
        return response.json()["message"]["content"]


# Create singleton instances
CHATGPT_API = ChatGPTAPI()
LLAMA_API = LLamaAPI()


def process_sentiment(data: DataFrame[BiasInput], upload=False) -> DataFrame[BiasInput]:
    data = data.dropna(subset=["url"])
    data = data.drop_duplicates(subset=["url"], keep=False)
    data["sentiment"] = data["sentiment"].str.lower()
    data = data.loc[data.sentiment.isin(settings.analysis.sentiment_categories)]
    split_title = data.title.str.split("|")

    data["title"] = split_title.apply(
        lambda x: x[np.argmax(np.array(list(map(len, x))))]
    ).values
    data.loc[data.source == "nytimes", "title"] = (
        data.loc[data.source == "nytimes", "title"]
        .str.split(" - The New York Times")
        .str[0]
    )
    data["title"] = data["title"].str.strip()
    data = data.loc[data.language == "en"]
    data = data.reset_index(drop=True)
    if upload:
        table_upload(df=data, primary_key="url", table_name="processed_news_articles")
    return data


def get_bias_stats(df):
    bias = (
        df.loc[df.sentiment.isin(["positive", "negative"])]
        .groupby(["source", "subject", "sentiment"])
        .size()
        .reset_index()
    )
    bias = bias.pivot(
        index=["source", "subject"], columns="sentiment", values=0
    ).reset_index()
    bias = bias.assign(positive=0) if "positive" not in bias.columns else bias
    bias = bias.assign(negative=0) if "negative" not in bias.columns else bias
    bias["num_news"] = bias["positive"] + bias["negative"]

    return bias


@upload_to_table(table_name="subject", primary_key="url")
def filter_subjects_of_interest(
    df: DataFrame[SitemapScrape],
    **kwargs
) -> DataFrame[SentimentDataInput]:
    df_subjects = pd.DataFrame()
    for subject in SUBJECTS:
        for alias in subject.split(" "):
            subject_df = df.loc[df.title.str.lower().str.contains(alias)]
        subject_df = subject_df.assign(subject=subject)
        df_subjects = pd.concat([df_subjects, subject_df])
    df_subjects = df_subjects.reset_index(drop=True)
    return df_subjects


@check_types
def build_inverse_bias(
    sentiment: DataFrame[BiasInput], upload=False
) -> DataFrame[InverseBiasOutput]:
    sentiment = get_table("sentiment")
    sentiment = pd.concat([sentiment, sentiment]).drop_duplicates(
        subset=["url"], keep="first"
    )
    binary_df = sentiment.loc[sentiment.sentiment.isin(["positive", "negative"])]
    df_bias = groupby_mode(binary_df, ["source", "subject"], "sentiment")
    sentiment = sentiment.merge(
        df_bias.rename(columns={"sentiment": "bias"}),
        how="left",
        on=["source", "subject"],
    )
    sentiment["inverse_bias"] = sentiment["bias"].map(
        {"positive": "negative", "negative": "positive", "N/A": "N/A"}
    )
    df_bias = sentiment.loc[sentiment.sentiment == sentiment.inverse_bias]
    df_bias = sentiment
    bias = get_bias_stats(df_bias)
    df_bias = sentiment.merge(
        bias[["source", "subject", "negative", "positive"]],
        how="left",
        on=["source", "subject"],
    )
    df_bias = df_bias.dropna(subset=["positive", "negative"])
    df_bias = df_bias.assign(negative=df_bias.negative.astype(pd.Int64Dtype()))
    df_bias = df_bias.assign(positive=df_bias.positive.astype(pd.Int64Dtype()))
    df_bias = df_bias.drop_duplicates(subset=["url"], keep="first")
    if upload:
        sql_replace_df(df=df_bias, primary_key="url", table_name="inverse_bias")
    return df_bias


def extract_judgement_from_text(text, subject, online=False):
    return ask_llm(
        question=(
            f"In the following news article title, can you classify how the author is portraying {subject}? "
            "Please classify as one of (negative,neutral,positive). "
            "If it's not clearly positive or negative, classify it as neutral. "
            "Please explain your classification in a single sentence. "
            "Represent the answer as a markdown table with three columns: subject, sentiment and explanation."
            f"\n\n'{text}'"
        ),
        llm_api=CHATGPT_API if online else LLAMA_API,
    )


def parse_markdown_table(markdown_text, scraped_content):
    cols = [
        "sentiment",
        "source",
        "subject",
        "explanation",
        "url",
        "publication_date",
        "language",
        "title",
    ]
    pattern = r"\|([^|]+)\|([^|]+)\|([^|]+)\|?"
    matches = re.findall(pattern, markdown_text)
    data_rows = matches[2:]
    parsed_data = []
    for row in data_rows:
        parsed_data.append(
            {
                "inferred_subject": row[0].strip(),
                "sentiment": row[1].strip(),
                "explanation": row[2].strip(),
            }
        )

    df = pd.DataFrame(parsed_data)
    df["source"] = scraped_content.source
    df["subject"] = scraped_content.subject
    df["url"] = scraped_content.url
    df["publication_date"] = scraped_content.publication_date
    df["language"] = scraped_content.language
    df["title"] = scraped_content.title
    if "explanation" not in df.columns:
        return pd.DataFrame()
    df = df.drop_duplicates(subset=["url"], keep=False)
    return df[cols]


def remove_already_inferred_sentiment(
    subject: DataFrame[SentimentDataInput],
) -> DataFrame[SentimentDataInput]:
    subject_db = get_table("unprocessed_sentiment", return_if_not_exists=True)
    if len(subject_db) == 0:
        return subject
    return subject.loc[~subject.url.isin(subject_db.url)].reset_index(drop=True)


@upload_to_table(table_name="sentiment", primary_key="url")
@check_types
def infer_sentiment(
    subject: DataFrame[SentimentDataInput], online=False, **kwargs
) -> DataFrame[BiasInput]:
    l = []
    subject = remove_already_inferred_sentiment(subject)
    print(f"Inferring sentiment for {len(subject)} rows.")
    if len(subject) == 0:
        return empty_dataframe_from_model(BiasInput)
    for i, row in subject.iterrows():
        if (i % 100) == 0:
            print(f"{i} of {len(subject)}: {100.*i/len(subject):.2f}% completed.")
        answer_example = extract_judgement_from_text(
            text=row["title"], subject=row["subject"], online=online
        )
        l.append(
            parse_markdown_table(
                answer_example,
                row,
            )
        )
    df = pd.concat(l)
    table_upload(
        df=df,
        primary_key="url",
        table_name="unprocessed_sentiment",
        verbose=True,
    )
    processed_sentiment = process_sentiment(df, upload=False)
    return processed_sentiment


def ask_llm(question, llm_api: LlmAPI = LLAMA_API):
    return llm_api.ask(question)
