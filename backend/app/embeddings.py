import os

import requests
from dotenv import load_dotenv


load_dotenv()


ACCOUNT_ID = os.getenv(
    "CLOUDFLARE_ACCOUNT_ID"
)

API_TOKEN = os.getenv(
    "CLOUDFLARE_API_TOKEN"
)


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
    f"https://api.cloudflare.com/client/v4/"
    f"accounts/{ACCOUNT_ID}/ai/run/{MODEL}"
)


HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


def embed_text(text: str):

    response = requests.post(
        BASE_URL,
        headers=HEADERS,
        json={
            "text": [text]
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    return data["result"]["data"][0]


def embed_texts(texts: list[str]):

    if not texts:
        return []

    response = requests.post(
        BASE_URL,
        headers=HEADERS,
        json={
            "text": texts
        },
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    return data["result"]["data"]