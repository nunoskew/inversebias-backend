from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from inversebias.data.db import InverseBiasEngine
from inversebias.config import settings
from contextlib import asynccontextmanager

from inversebias.data.storage import download_db


class NewsArticle(BaseModel):
    source: str
    subject: str
    url: str
    title: str
    sentiment: str
    publication_date: str
    explanation: str
    num_negative: int
    num_positive: int
    bias: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    download_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.api.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/articles", response_model=List[NewsArticle])
def get_articles(
    limit: int = Query(settings.api.default_limit, le=settings.api.max_limit),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    subject: Optional[str] = None,
    sentiment: Optional[str] = None,
):

    query = (
        "SELECT source, subject, url, title, "
        "publication_date, sentiment, explanation,bias,negative "
        "as num_negative,positive as num_positive FROM inverse_bias WHERE 1=1"
    )
    params = {}

    if source:
        query += " AND source = :source"
        params.update({"source": source})

    if subject:
        query += " AND subject = :subject"
        params.update({"subject": subject})

    if sentiment:
        query += " AND sentiment = :sentiment"
        params.update({"sentiment": sentiment})

    query += " ORDER BY publication_date DESC LIMIT :limit OFFSET :offset"
    params.update({"limit": limit, "offset": offset})
    engine = InverseBiasEngine().engine

    with engine.connect() as conn:
        articles = [
            NewsArticle(**row)
            for row in conn.execute(text(query), parameters=params).mappings().all()
        ]
    return articles


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api.host, port=settings.api.port)
