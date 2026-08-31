import os
import time
import random
import requests
from dotenv import load_dotenv


load_dotenv()


ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")


if not ACCOUNT_ID:
    raise ValueError(
        "CLOUDFLARE_ACCOUNT_ID is not set"
    )

if not API_TOKEN:
    raise ValueError(
        "CLOUDFLARE_API_TOKEN is not set"
    )


MODEL = "@cf/baai/bge-small-en-v1.5"

BASE_URL = (
    "https://api.cloudflare.com/client/v4/"
    f"accounts/{ACCOUNT_ID}/ai/run/{MODEL}"
)


HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


MAX_RETRIES = 6
INITIAL_BACKOFF = 2
MAX_BACKOFF = 60

# Minimum delay between embedding requests.
# This prevents us from continuously hammering the API.
REQUEST_DELAY = 1.0

_last_request_time = 0.0


def _wait_before_request():
    global _last_request_time

    elapsed = time.monotonic() - _last_request_time

    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)


def _request_embeddings(texts: list[str]):
    global _last_request_time

    if not texts:
        return []

    for attempt in range(MAX_RETRIES):
        _wait_before_request()

        try:
            response = requests.post(
                BASE_URL,
                headers=HEADERS,
                json={
                    "text": texts
                },
                timeout=120,
            )

            _last_request_time = time.monotonic()

        except requests.RequestException as error:
            if attempt == MAX_RETRIES - 1:
                raise

            wait_time = min(
                INITIAL_BACKOFF * (2 ** attempt),
                MAX_BACKOFF,
            )

            # Add a little randomness so repeated requests
            # don't all retry at exactly the same time.
            wait_time += random.uniform(0, 1)

            print(
                f"Embedding request failed. "
                f"Retrying in {wait_time:.1f}s "
                f"(attempt {attempt + 1}/{MAX_RETRIES})..."
            )

            time.sleep(wait_time)
            continue

        if response.status_code == 429:
            if attempt == MAX_RETRIES - 1:
                response.raise_for_status()

            retry_after = response.headers.get(
                "Retry-After"
            )

            if retry_after:
                try:
                    wait_time = float(retry_after)
                except ValueError:
                    wait_time = INITIAL_BACKOFF * (
                        2 ** attempt
                    )
            else:
                wait_time = INITIAL_BACKOFF * (
                    2 ** attempt
                )

            wait_time = min(
                wait_time,
                MAX_BACKOFF,
            )

            wait_time += random.uniform(0, 1)

            print(
                f"Cloudflare rate limit reached. "
                f"Retrying in {wait_time:.1f}s "
                f"(attempt {attempt + 1}/{MAX_RETRIES})..."
            )

            time.sleep(wait_time)
            continue

        response.raise_for_status()

        data = response.json()

        if (
            "result" not in data
            or "data" not in data["result"]
        ):
            raise RuntimeError(
                "Unexpected embedding API response."
            )

        embeddings = data["result"]["data"]

        if len(embeddings) != len(texts):
            raise RuntimeError(
                "Embedding count does not match input count."
            )

        return embeddings

    raise RuntimeError(
        "Failed to generate embeddings after retries."
    )


def embed_text(text: str):
    embeddings = _request_embeddings(
        [text]
    )

    return embeddings[0]


def embed_texts(texts: list[str]):
    if not texts:
        return []

    return _request_embeddings(texts)