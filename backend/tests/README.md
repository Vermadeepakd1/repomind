# Backend tests

## Unit tests (default)

```bash
cd backend
python -m unittest discover -s tests
```

These tests are hermetic. `tests/_env.py` replaces every credential with a dummy value before the application is imported, so your `backend/.env` (which may point at production services) is never used. The database, embedding provider, and Gemini are mocked. Qdrant behaviour is exercised against qdrant-client's in-memory engine. The test client never enters the app lifespan, so no database connection is made.

Every test module must start with:

```python
from tests import _env  # noqa: F401  (must run before app imports)
```

`fastapi.testclient` needs `httpx`, which is included in `requirements-dev.txt`.

## Live end-to-end test (opt-in)

`test_e2e.py` registers a user, indexes a real repository, and asks a question through the configured database, Qdrant, Cloudflare, and Gemini services. With `REPO_MIND_RUN_E2E=1`, the dummy credentials are not applied and the real `.env` is used.

```bash
cd backend
REPO_MIND_RUN_E2E=1 REPO_MIND_E2E_REPO_URL=https://github.com/user/test-repository python -m unittest tests.test_e2e
```

Run it only against a dedicated test database and Qdrant collection. It creates real users and data and consumes provider quota.
