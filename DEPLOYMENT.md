# RepoMind deployment checklist

## Backend

The backend does not need `git`. Repositories are streamed from GitHub's tarball endpoint, and only indexable source files (at most 50 MB per job) are written to the temporary directory, so it fits on hosts with limited disk such as Render.

Install production dependencies only:

```bash
pip install -r requirements.txt
```

Run the backend from the `backend` directory with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
```

`--proxy-headers` makes the API see the real client IP behind the platform's load balancer, which the per-IP login and sign-up rate limits rely on. Only trust all forwarded IPs (`"*"`) when the app is reachable exclusively through the platform proxy; otherwise list the proxy addresses instead. The per-email login limit does not depend on this setting.

Run a single worker process. Indexing jobs run in the API process as background tasks, and on startup any job left `queued` or `running` is marked as interrupted.

Configure these server-side variables:

- `DATABASE_URL`
- `JWT_SECRET`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `QDRANT_URL` and `QDRANT_API_KEY` when using hosted Qdrant
- `FRONTEND_URL` with the exact HTTPS frontend origin

Database tables, columns, and indexes are created or migrated automatically on startup. The Qdrant collection and its payload indexes are created on first indexing.

The backend exposes `/health` for platform health checks. Do not expose `.env` files or provider credentials to the frontend.

### Upgrading existing data

- Repositories indexed before index versioning keep working. Their first reindex replaces the old, unversioned chunks.
- Repository URLs are now canonicalised (no `www.` or `.git` suffix). A repository that was originally indexed with a `www.github.com` or `.git` URL gets a new ID, so delete it and index it again.
- Indexing jobs created before this release have no owner and can no longer be looked up. They are historical records only.

## Frontend

Set `VITE_API_URL` to the deployed backend URL before building:

```bash
VITE_API_URL=https://api.example.com npm run build
```

The frontend should be served over HTTPS, and the same origin should be configured as `FRONTEND_URL` on the backend.
