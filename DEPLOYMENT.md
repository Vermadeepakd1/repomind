# RepoMind deployment checklist

## Backend

Run the backend from the `backend` directory with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Configure these server-side variables:

- `DATABASE_URL`
- `JWT_SECRET`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `QDRANT_URL` and `QDRANT_API_KEY` when using hosted Qdrant
- `FRONTEND_URL` with the exact HTTPS frontend origin

The backend exposes `/health` for platform health checks. Do not expose `.env` files or provider credentials to the frontend.

## Frontend

Set `VITE_API_URL` to the deployed backend URL before building:

```bash
VITE_API_URL=https://api.example.com npm run build
```

The frontend should be served over HTTPS, and the same origin should be configured as `FRONTEND_URL` on the backend.
