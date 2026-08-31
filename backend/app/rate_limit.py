from collections import defaultdict, deque
from threading import Lock
import time


_requests = defaultdict(deque)
_lock = Lock()


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    now = time.monotonic()
    cutoff = now - window_seconds

    with _lock:
        timestamps = _requests[key]
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= limit:
            return False

        timestamps.append(now)
        return True
