import random
import time
from collections.abc import Callable


def retry_call(
    operation: Callable,
    operation_name: str,
    attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 8.0,
):
    """Retry provider calls with bounded exponential backoff."""
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as error:
            if attempt == attempts - 1:
                raise

            delay = min(initial_delay * (2 ** attempt), max_delay)
            delay += random.uniform(0, 0.25)
            print(
                f"{operation_name} failed ({type(error).__name__}: {error}). "
                f"Retrying in {delay:.1f}s "
                f"(attempt {attempt + 1}/{attempts})..."
            )
            time.sleep(delay)

    raise RuntimeError(f"{operation_name} failed after retries.")
