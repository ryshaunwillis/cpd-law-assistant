import os
import requests
import time

OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"

def embed_texts(texts):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    embeddings = []

    for i, text in enumerate(texts):
        payload = {
            "model": model,
            "input": text
        }

        retries = 0
        max_retries = 6

        while True:
            try:
                r = requests.post(
                    OPENAI_EMBED_URL,
                    headers=headers,
                    json=payload,
                    timeout=60
                )

                if r.status_code == 429:
                    wait = min(2 ** retries, 20)
                    print(f"Rate limit hit. Sleeping {wait} seconds...")
                    time.sleep(wait)
                    retries += 1
                    if retries > max_retries:
                        r.raise_for_status()
                    continue

                if r.status_code in (500, 502, 503, 504):
                    wait = min(2 ** retries, 20)
                    print(f"OpenAI server error {r.status_code}. Retrying in {wait} seconds...")
                    time.sleep(wait)
                    retries += 1
                    if retries > max_retries:
                        try:
                            print(f"\n[EMBED ERROR] status={r.status_code} chunk_index={i} chunk_len={len(text)}")
                            print(r.json())
                        except Exception:
                            print(r.text)
                        r.raise_for_status()
                    continue

                if r.status_code >= 400:
                    try:
                        print(f"\n[EMBED ERROR] status={r.status_code} chunk_index={i} chunk_len={len(text)}")
                        print(r.json())
                    except Exception:
                        print(r.text)
                    r.raise_for_status()

                data = r.json()
                embeddings.append(data["data"][0]["embedding"])
                break

            except requests.RequestException as e:
                wait = min(2 ** retries, 20)
                print(f"Request failed ({e}). Retrying in {wait} seconds...")
                time.sleep(wait)
                retries += 1
                if retries > max_retries:
                    raise

    return embeddings