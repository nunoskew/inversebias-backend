from dataclasses import dataclass
import re
from typing import List, Dict, Any

from bs4 import BeautifulSoup, Tag
import pandas as pd
from urllib3 import Retry
from inversebias.config.settings import SOURCE_TO_URL
from inversebias.data.db import upload_to_table
from inversebias.data.df_schema import (
    SitemapScrape,
    SitemapTmpScrape,
)

import os
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dataclasses import asdict, dataclass
from typing import List
from pandera.typing import DataFrame
from inversebias.data.utils import SOURCE_TO_URL


@dataclass
class StandardScrapePayload:
    url: str
    formats: List[str]
    onlyMainContent: bool
    excludeTags: List[str]
    includeTags: List[str]


@dataclass
class PromptExtract:
    prompt: str


@dataclass
class LLMScrapePayload:
    url: str
    formats: List[str]
    extract: PromptExtract


@dataclass
class SitemapScrapePayload:
    url: str
    search: str
    ignoreSitemap: bool
    includeSubdomains: bool
    limit: int


@upload_to_table(table_name="title", primary_key="url")
def build_today(**kwargs) -> DataFrame[SitemapScrape]:
    today = pd.concat(
        [sitemap_scrape(news_entity) for news_entity in SOURCE_TO_URL.keys()]
    )
    return today


def scrape(
    scrape_payload: StandardScrapePayload | LLMScrapePayload | SitemapScrapePayload,
    opt="scrape",
):
    opt_dict = {
        "scrape": "data",
        "map": "links",
    }
    retry_strategy = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        url = "https://api.firecrawl.dev/v1/" + opt
        payload = asdict(scrape_payload)
        headers = {
            "Authorization": f"Bearer {os.getenv('API_KEY')}",
            "Content-Type": "application/json",
        }
        response = session.post(url, json=payload, headers=headers)
        scrape_result = response.json()
        if opt_dict[opt] not in scrape_result:
            print(f"Scrape failed: {scrape_result}")
            return None
        return scrape_result[opt_dict[opt]]
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


def standard_scrape(url, formats=["markdown", "html"], include_tags=[]):
    print(f"Scraping {url}")
    payload = StandardScrapePayload(
        url=url,
        formats=formats,
        onlyMainContent=True,
        excludeTags=["script", "style", ".ad", "#footer"],
        includeTags=include_tags,
    )
    scraped_content = scrape(scrape_payload=payload)

    return scraped_content


def sitemap_scrape(
    news_source: str,
) -> SitemapScrape:
    url = SOURCE_TO_URL[news_source]["sitemap_url"]
    df = _sitemap_scrape(url)
    df["source"] = news_source
    return df


def _sitemap_scrape(url: str) -> SitemapTmpScrape:
    sitemap: Dict[str, Any] = standard_scrape(url, include_tags=["url"])
    sitemap_soup: BeautifulSoup = BeautifulSoup(sitemap["html"], features="lxml")
    scrape: pd.DataFrame = pd.concat(
        [_parse_url_xml(url) for url in sitemap_soup.find_all("url")]
    ).dropna()
    return scrape


def _parse_url_xml(url_xml: Tag) -> SitemapTmpScrape:
    url: str = url_xml.find_next("loc").contents[0]

    def _extract_url_contents(url_xml: Tag) -> List[str]:
        """
        Extract news-specific metadata from a URL XML element.

        Args:
            url_xml (bs4.Tag): A BeautifulSoup Tag object representing a <url> element.

        Returns:
            List[str]: A list of extracted metadata values.
        """
        fields = ["title", "language", "publication_date"]
        df = pd.DataFrame(
            [
                {
                    field: getattr(url_xml.find(f"news:{field}"), "contents", [None])[0]
                    for field in fields
                }
            ]
        )
        return df

    df = _extract_url_contents(url_xml)
    df["url"] = url
    return df
