# Backend integration tests

The API tests are opt-in because importing the application initializes the configured database and provider clients.

Configure a dedicated test database and the normal backend environment variables, then run:

```bash
cd backend
REPO_MIND_RUN_API_TESTS=1 python -m unittest discover -s tests
```

These tests do not index a real repository or call Gemini, Cloudflare, or Qdrant. A separate end-to-end test should use an isolated database/vector collection and an explicitly configured public test repository before exercising the full indexing flow.

The live end-to-end flow is intentionally separate:

```bash
cd backend
REPO_MIND_RUN_E2E=1 REPO_MIND_E2E_REPO_URL=https://github.com/user/test-repository python -m unittest tests.test_e2e
```

Run it only with a dedicated test database and vector collection; it uses the configured embedding and LLM providers.
