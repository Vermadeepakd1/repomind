import hashlib


def get_repository_id(repo_url: str, user_id: str | None = None) -> str:

    normalized_url = repo_url.strip().lower().rstrip("/")

    identity = f"{user_id or 'global'}:{normalized_url}"

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()[:16]
