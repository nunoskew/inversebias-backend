import pandera as pa
from pandera.typing import Series


class ScrapeInput(pa.DataFrameModel):
    source: Series[str] = pa.Field(coerce=False)
    subject: Series[str] = pa.Field(coerce=False)
    url: Series[str] = pa.Field(coerce=False)



class SitemapTmpScrape(pa.DataFrameModel):
    url: Series[str] = pa.Field(coerce=False)
    title: Series[str] = pa.Field(coerce=False)
    publication_date: Series[str] = pa.Field(coerce=False)
    language: Series[str] = pa.Field(coerce=False)


class SitemapScrape(pa.DataFrameModel):
    source: Series[str] = pa.Field(coerce=False)



class TodaysScrape(pa.DataFrameModel):
    source: Series[str] = pa.Field(coerce=False)
    subject: Series[str] = pa.Field(coerce=False)
    url: Series[str] = pa.Field(coerce=False)
    title: Series[str] = pa.Field(coerce=False)


class UnprocessedScrapedContent(pa.DataFrameModel):
    source: Series[str] = pa.Field(coerce=False)
    subject: Series[str] = pa.Field(coerce=False)
    url: Series[str] = pa.Field(coerce=False)
    content: Series[str] = pa.Field(coerce=False)


class SentimentDataInput(pa.DataFrameModel):
    source: Series[str] = pa.Field(coerce=False)
    subject: Series[str] = pa.Field(coerce=False)
    url: Series[str] = pa.Field(coerce=False)
    publication_date: Series[str] = pa.Field(coerce=False)
    language: Series[str] = pa.Field(coerce=False)
    title: Series[str] = pa.Field(coerce=False)


class BiasInput(pa.DataFrameModel):
    source: Series[str] = pa.Field(coerce=False)
    subject: Series[str] = pa.Field(coerce=False)
    url: Series[str] = pa.Field(coerce=False)
    publication_date: Series[str] = pa.Field(coerce=False)
    language: Series[str] = pa.Field(coerce=False)
    title: Series[str] = pa.Field(coerce=False)
    sentiment: Series[str] = pa.Field(coerce=False)
    explanation: Series[str] = pa.Field(coerce=False)


class InverseBiasOutput(pa.DataFrameModel):
    source: Series[str] = pa.Field(coerce=False)
    subject: Series[str] = pa.Field(coerce=False)
    url: Series[str] = pa.Field(coerce=False)
    publication_date: Series[str] = pa.Field(coerce=False)
    language: Series[str] = pa.Field(coerce=False)
    title: Series[str] = pa.Field(coerce=False)
    sentiment: Series[str] = pa.Field(coerce=False)
    explanation: Series[str] = pa.Field(coerce=False)
    bias: Series[str] = pa.Field(coerce=False)
    inverse_bias: Series[str] = pa.Field(coerce=False)
    negative: Series[int] = pa.Field(coerce=False)
    positive: Series[int] = pa.Field(coerce=False)
