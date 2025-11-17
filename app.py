import os
import re
from dataclasses import asdict, dataclass
from typing import Optional

import ollama
from goose3 import Goose
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)

DEFAULT_MODEL = "llama3"
DEFAULT_TRUNCATION = 1000
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)

PROMPT_TEMPLATE = """
You are a misinformation detection expert.

Analyze the following online content for credibility:
\"\"\"{content}\"\"\"

Step 1: Identify if the text contains misleading, exaggerated, or false claims.
Step 2: Detect patterns typical of misinformation.
Step 3: Output a credibility score from 0 (false) to 100 (credible) and a reason.

Respond in this format only:
Credibility Score: <score>
Reason: <brief reason>
""".strip()

_RE_PARSE = re.compile(r"Credibility Score:\s*(\d+)\s*Reason:\s*(.*)", re.DOTALL)
_GOOSE = Goose()


@dataclass
class CredibilityResult:
    article: str
    score: Optional[int]
    reason: str

    def serialize(self, truncate_at: int = DEFAULT_TRUNCATION) -> dict:
        payload = asdict(self)
        if self.article:
            payload["article"] = self.article[: truncate_at or DEFAULT_TRUNCATION]
        payload["score"] = self.score
        return payload


def extract_article_from_url(url: str) -> str:
    article = _GOOSE.extract(url=url)
    if not article or not article.cleaned_text:
        raise ValueError("Unable to extract article text from the provided URL.")
    return article.cleaned_text.strip()


def _parse_model_response(content: str) -> tuple[Optional[int], str]:
    if not content:
        return None, "Empty response from model."

    match = _RE_PARSE.search(content)
    if not match:
        return None, "Unable to parse credibility score from model response."

    score = int(match.group(1))
    reason = match.group(2).strip()
    return score, reason


def check_credibility(text: str) -> CredibilityResult:
    messages = [
        {"role": "system", "content": "You specialize in credibility analysis."},
        {"role": "user", "content": PROMPT_TEMPLATE.format(content=text)},
    ]
    response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
    content = response["message"]["content"]
    score, reason = _parse_model_response(content)
    return CredibilityResult(article=text, score=score, reason=reason)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.post("/api/check")
def api_check():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({"message": "URL is required."}), 400

    try:
        article = extract_article_from_url(url)
        result = check_credibility(article)
        return jsonify(result.serialize())
    except Exception as exc:
        return jsonify({"message": str(exc)}), 500


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug_mode)
