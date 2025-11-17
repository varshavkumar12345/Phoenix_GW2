import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Optional

import chromadb
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from goose3 import Goose

load_dotenv()

EMBEDDING_MODEL = "mistral-embed"
COLLECTION_NAME = "news"
COSINE_THRESHOLD = 0.57
DEFAULT_MODEL = "mistral-small-latest"
DEFAULT_API_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_EMBED_URL = "https://api.mistral.ai/v1/embeddings"
DEFAULT_TRUNCATION = 1000

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", DEFAULT_MODEL)
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", DEFAULT_API_URL)
MISTRAL_EMBED_MODEL = os.getenv("MISTRAL_EMBED_MODEL", EMBEDDING_MODEL)
MISTRAL_EMBED_URL = os.getenv("MISTRAL_EMBED_URL", DEFAULT_EMBED_URL)

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)

PROMPT_TEMPLATE = """
You are a misinformation detection expert.

You are given news snippets retrieved from a vector database based on an input article URL.
Use ONLY these snippets as evidence when judging credibility of that article.

Snippets:
\"\"\"{content}\"\"\"

Step 1: Identify if the information in these snippets appears misleading, exaggerated, or false.
Step 2: Detect patterns typical of misinformation.
Step 3: Output a credibility score from 0 (false) to 100 (credible) and a reason.

Respond in this format only:
Credibility Score: <score>
Reason: <brief reason>
""".strip()

_RE_PARSE = re.compile(r"Credibility Score:\s*(\d+)\s*Reason:\s*(.*)", re.DOTALL)
URL_PATTERN = re.compile(r"https?://[^\s\"')>\]]+")
_GOOSE = Goose()


@dataclass
class CredibilityResult:
    article: str
    snippets: str
    score: Optional[int]
    reason: str

    def serialize(self, truncate_at: int = DEFAULT_TRUNCATION) -> dict:
        payload = asdict(self)
        if self.article:
            payload["article"] = self.article[: truncate_at or DEFAULT_TRUNCATION]
        if self.snippets:
            payload["snippets"] = self.snippets[: truncate_at or DEFAULT_TRUNCATION]
        payload["score"] = self.score
        return payload


def extract_article_from_url(url: str) -> str:
    article = _GOOSE.extract(url=url)
    if not article or not article.cleaned_text:
        raise ValueError("Unable to extract article text from the provided URL.")
    return article.cleaned_text.strip()


def _get_embedding(text: str) -> list[float]:
    if not MISTRAL_API_KEY:
        raise RuntimeError(
            "MISTRAL_API_KEY is not set. Please define it in your environment or .env file."
        )

    response = requests.post(
        MISTRAL_EMBED_URL,
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": MISTRAL_EMBED_MODEL, "input": text},
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Mistral embedding API error {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    embedding = data.get("data", [{}])[0].get("embedding")
    if not embedding:
        raise RuntimeError("Embedding response did not include vector data.")
    return embedding


def retrieve(query: str, top_n: int = 3) -> list[str]:
    """Embed the query with Mistral and retrieve similar docs from ChromaDB."""
    qe = _get_embedding(query)
    results = collection.query(
        query_embeddings=[qe], n_results=top_n, include=["documents", "distances"]
    )

    docs = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    filtered = [
        doc
        for doc, distance in zip(docs, distances)
        if distance is not None and (1 - distance) >= COSINE_THRESHOLD
    ]

    return filtered


def extract_reference_link(doc):
    if not doc:
        return None

    if isinstance(doc, dict):
        for key in ("link", "url", "source"):
            value = doc.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value

    if isinstance(doc, str):
        try:
            parsed = json.loads(doc)
            if isinstance(parsed, dict):
                ref = parsed.get("link") or parsed.get("url")
                if isinstance(ref, str) and ref.startswith("http"):
                    return ref
        except json.JSONDecodeError:
            pass

        match = URL_PATTERN.search(doc)
        if match:
            return match.group(0).rstrip(".,);")

    return None


def _parse_model_response(content: str) -> tuple[Optional[int], str]:
    if not content:
        return None, "Empty response from model."

    match = _RE_PARSE.search(content)
    if not match:
        return None, "Unable to parse credibility score from model response."

    score = int(match.group(1))
    reason = match.group(2).strip()
    return score, reason


def check_credibility(snippets: str) -> CredibilityResult:
    if not MISTRAL_API_KEY:
        raise RuntimeError(
            "MISTRAL_API_KEY is not set. Please define it in your environment or .env file."
        )

    payload = {
        "model": MISTRAL_MODEL,
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(content=snippets)}],
        "temperature": 0,
    }

    response = requests.post(
        MISTRAL_API_URL,
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Mistral API error {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    score, reason = _parse_model_response(content)
    # article will be filled in api_check, we just keep the structure here
    return CredibilityResult(article="", snippets=snippets, score=score, reason=reason)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.post("/api/check")
def api_check():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    top_n = data.get("top_n", 3)

    if not url:
        return jsonify({"message": "URL is required."}), 400

    try:
        # Extract article text from the URL
        article = extract_article_from_url(url)

        try:
            top_n = max(1, int(top_n))
        except (TypeError, ValueError):
            top_n = 3

        # Use the article text as the query into your vector DB
        documents = retrieve(article, top_n=top_n)
        snippets = " ".join(documents) if documents else ""
        result = check_credibility(snippets or article)
        reference_links = [
            link for link in (extract_reference_link(doc) for doc in documents) if link
        ]

        payload = result.serialize()
        payload["article"] = article[:DEFAULT_TRUNCATION]
        payload["url"] = url
        payload["documents"] = reference_links
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"message": str(exc)}), 500


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug_mode)
