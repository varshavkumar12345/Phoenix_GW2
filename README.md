#     RAG Enabled Credibility Checker

This project uses RAG and LLMs to calculate the credibility score of any website. Supply a news/article URL and the app will:

1. Fetch and clean the article text with Goose.
2. Score the article’s credibility using a local Ollama `llama3` model and a structured prompt.
3. Return the score, reasoning, and an excerpt of the extracted article to the browser UI at `/`.

The repository also contains a Scrapy crawler and ChromaDB embedding script (legacy RAG flow).

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Ensure you have:

- Python 3.10+
- Ollama installed locally with the `llama3` model pulled (e.g., `ollama pull llama3`)
- (Optional) ChromeDriver/other tooling if you plan to extend scraping

## Environment

Key environment variables:

| Variable        | Purpose                                   | Default |
|-----------------|-------------------------------------------|---------|
| `OLLAMA_MODEL`  | Local Ollama model to query               | llama3  |
| `FLASK_DEBUG`   | Enables Flask debug mode if set to `true` | false   |
| `PORT`          | Flask port                                | 5000    |

## Running the App

1. Start Ollama (`ollama serve`) if it isn’t already running.
2. Launch the Flask server:

```bash
python retrieve.py
```

3. Visit `http://localhost:5000` and submit an article URL. The page will display the credibility score, reason, and extracted text snippet.

## Additional Scripts

- `web_crawler.py`: Scrapy spider for collecting news articles into `googlenews.json`.
- `embedding.py`: Loads scraped stories into ChromaDB with Ollama embeddings (used by the earlier RAG workflow).

These components are optional for the credibility checker but remain available if you need to regenerate context data.

