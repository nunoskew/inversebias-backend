# [inversebias](https://inversebias.com)



inversebias scrapes news sources, analyzes the sentiment of the headlines, and determines if there's an "inverse bias" - where the sentiment of an article contradicts the known political leaning of its source.

## Features

- **News Scraping**: Automatically collects articles from various news sources
- **Sentiment Analysis**: Uses LLM-based approaches to determine the sentiment of news articles
- **Bias Detection**: Identifies when news outlets publish content that contradicts their typical political leaning
- **API Endpoints**: FastAPI-based service to query analyzed articles

## Installation

### Prerequisites

- Python 3.10+
- Poetry (dependency management)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/inversebias-backend.git
   cd inversebias-backend
   ```

2. Install dependencies:

   ```bash
   poetry install
   ```

3. Set up environment variables (create a `.env` file):
   ```
   OPENAI_API_KEY=your_openai_key_here
   ```

## Usage

### Running the API server

```bash
poetry run python -m inversebias.api
```

The API will be available at http://localhost:8000

### API Endpoints

- `GET /articles` - Retrieve analyzed news articles with filtering options:
  - `limit`: Maximum number of articles to return
  - `offset`: Number of articles to skip (for pagination)
  - `source`: Filter by news source
  - `subject`: Filter by article subject
  - `sentiment`: Filter by detected sentiment

## Data Pipeline

1. **Scraping**: The system scrapes news article content using the `scrape.py` module
2. **Subject Classification**: Filters articles to those covering subjects of interest
3. **Sentiment Analysis**: Uses LLM models to analyze sentiment of articles
4. **Bias Detection**: Compares the detected sentiment against the known bias of the source
5. **Database Storage**: Stores results in an SQLite database

## Development

### Project Structure

- `inversebias/api.py`: FastAPI implementation for serving article data
- `inversebias/ml.py`: Machine learning components for sentiment analysis
- `inversebias/scrape.py`: Web scraping functionality for news articles
- `inversebias/data/`: Database schemas and utilities
- `tests/`: Unit and integration tests

### Running Tests

```bash
poetry run pytest
```

For tests with coverage:

```bash
poetry run pytest --cov=inversebias
```

