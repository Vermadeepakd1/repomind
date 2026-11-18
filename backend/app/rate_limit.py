import logging
from datetime import datetime, timezone


logger = logging.getLogger("repomind.rate_limit")


def _window_start(window_seconds: int, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(epoch - epoch % window_seconds, tz=timezone.utc)


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    """Fixed-window rate limit shared by every backend process via PostgreSQL.

    Returns True when the request is allowed. If the counter store is
    unavailable the request is allowed (fail open) so a database hiccup does
    not lock every user out; the failure is logged.
    """
    from app.repository_store import increment_rate_limit

    try:
        hits = increment_rate_limit(key, _window_start(window_seconds))
    except Exception:
        logger.exception("Rate limit check failed for %s", key)
        return True

    return hits <= limit
