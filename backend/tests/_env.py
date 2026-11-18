"""Force dummy provider settings so unit tests never reach real services.

Application modules call ``load_dotenv()``, which does not override variables
that are already set. Setting placeholders here (before any ``app`` import)
guarantees the developer's ``backend/.env`` -- which may point at production
databases and paid APIs -- is never used by the hermetic test suite.

The opt-in live end-to-end test sets ``REPO_MIND_RUN_E2E=1`` and needs the
real configuration, so the placeholders are skipped in that case.
"""
import os


DUMMY_ENVIRONMENT = {
    "DATABASE_URL": "postgresql://test:test@127.0.0.1:1/repomind_unit_tests",
    "JWT_SECRET": "unit-test-secret",
    "GEMINI_API_KEY": "unit-test-gemini-key",
    "GEMINI_MODEL": "unit-test-model",
    "CLOUDFLARE_ACCOUNT_ID": "unit-test-account",
    "CLOUDFLARE_API_TOKEN": "unit-test-token",
    "QDRANT_URL": "http://127.0.0.1:1",
    "QDRANT_API_KEY": "unit-test-qdrant-key",
}

if os.getenv("REPO_MIND_RUN_E2E") != "1":
    os.environ.update(DUMMY_ENVIRONMENT)
