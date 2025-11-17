# Credibility Checker

Drop in a news/article URL and the app will:

1. Fetch and clean the article text with Goose.
2. Embed the article via Ollama, retrieve similar context from your local Chroma store, and send those snippets to the hosted Mistral API for credibility scoring.
3. Return the score, reasoning, retrieved snippets, and an excerpt of the article to the UI at `/`.

The repo also ships a Scrapy crawler and Chroma ingestion script (legacy RAG workflow) if you need to refresh your corpus.

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

You’ll need:

- Python 3.10+
- Ollama (for `nomic-embed-text` embeddings)
- A Mistral API key (`mistral-small-latest` by default)
- (Optional) ChromeDriver or other scraping add-ons

## Environment

| Variable          | Purpose                                           | Default                               |
|-------------------|---------------------------------------------------|---------------------------------------|
| `MISTRAL_API_KEY` | API key for Mistral chat completions (required)   | —                                     |
| `MISTRAL_MODEL`   | Hosted model ID                                   | `mistral-small-latest`                |
| `MISTRAL_API_URL` | Endpoint for chat completions                     | `https://api.mistral.ai/v1/chat/completions` |
| `FLASK_DEBUG`     | Enables Flask debug mode if set to `true`         | `false`                               |
| `PORT`            | Flask port                                        | `5000`                                |

## Run locally

```bash
python retrieve.py
```

Open `http://localhost:5000`, paste a URL, and the dashboard will display the credibility score, reason, retrieved snippets, and article preview.

## Extras

- `web_crawler.py`: Scrapy spider that prepends fresh Google News entries into `googlenews.json`.
- `embedding.py`: Loads scraped stories into your Chroma DB with Ollama embeddings (useful for refreshing context).

