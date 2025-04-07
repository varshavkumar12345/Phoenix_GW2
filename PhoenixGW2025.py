import requests
import re
from goose3 import Goose

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

# === MAIN ===
if __name__ == "__main__":
    url = input("Enter the news article URL: ")
    try:
        article_text = extract_article_from_url(url)
        print(f"\n->Extracted Article:\n{article_text[:500]}...")  # Optional preview
        score, reason = check_credibility(article_text)
        print(f"\n=>Score: {score}/100")
        print(f"Reason: {reason}")
    except Exception as e:
        print(f"Error: {e}")