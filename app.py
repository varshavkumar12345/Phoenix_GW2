from flask import Flask, request, jsonify
from flask_cors import CORS
from goose3 import Goose
import requests
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

MISTRAL_API_KEY = "e6ojRsfwNwYFzpVQjpHtX8YavnOrIjcI"
MODEL = "mistral-small-latest"
API_URL = "https://api.mistral.ai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

def extract_article_from_url(url):
    g = Goose()
    article = g.extract(url=url)
    return article.cleaned_text.strip()

def check_credibility(text):
    prompt = f"""
You are a misinformation detection expert.

Analyze the following online content for credibility:
\"\"\"{text}\"\"\"

Step 1: Identify if the text contains misleading, exaggerated, or false claims.
Step 2: Detect patterns typical of misinformation.
Step 3: Output a credibility score from 0 (false) to 100 (credible) and a reason.

Respond in this format only:
Credibility Score: <score>
Reason: <brief reason>
"""
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(API_URL, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code} - {response.text}")

    content = response.json()['choices'][0]['message']['content']
    match = re.search(r"Credibility Score: (\d+)\s*Reason: (.*)", content, re.DOTALL)


    if match:
        score = int(match.group(1))
        reason = match.group(2).strip()
        return score, reason
    else:
        return None, "Couldn't parse response."

@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"message": "URL is required"}), 400

    try:
        article = extract_article_from_url(url)
        score, reason = check_credibility(article)
        return jsonify({
            "article": article[:1000],  # Optional limit
            "score": score,
            "reason": reason
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
