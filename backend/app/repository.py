import hashlib


def get_repository_id(repo_url: str) -> str:

    normalized_url = repo_url.strip().lower().rstrip("/")

    return hashlib.sha256(
        normalized_url.encode("utf-8")
    ).hexdigest()[:16]