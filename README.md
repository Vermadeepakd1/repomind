# RepoMind

RepoMind is an AI-powered workspace for understanding public GitHub repositories. Index a repository, ask questions in plain language, and get answers grounded in the code with source references.

## What it does

- Indexes public GitHub repositories in the background, with live progress.
- Splits source into searchable code chunks, embeds them with Cloudflare Workers AI (`bge-small-en-v1.5`), and stores the vectors in Qdrant.
- Retrieves and reranks the most relevant chunks, then uses Gemini to answer from that context.
- Keeps accounts, repositories, chat sessions, and message history in PostgreSQL. Chats are titled automatically from their first question.
- Lets you browse indexed files, reindex, delete repositories, and switch between or delete chats.

RepoMind supports public repositories only. It does not request or store GitHub credentials.

## How indexing works

1. The default branch is streamed from GitHub's tarball endpoint (no `git` binary and no history). Only regular files with supported extensions are written to a temporary directory; dependency/build folders, files over 500 KB, symlinks, hard links, and paths that would escape the directory are skipped. Downloads are capped at 200 MB compressed and 3 minutes, and extraction stops at 50 MB of source, so disk use per job stays small.
2. The extracted files are read as UTF-8 source (empty or binary files are skipped). Limit: 2,000 files per repository.
3. Files are chunked, embedded, and written to Qdrant under a new **index version**.
4. Only when every chunk is stored does the repository switch to the new version; older chunks are then removed. If indexing fails, the partial new version is discarded and the previous index keeps working.

Repository URLs are canonicalised (`www.`, trailing `/`, and `.git` are ignored), so the same repository is never indexed twice under different URLs.

## Project structure

```text
repomind/
├── backend/
│   ├── app/       FastAPI API, indexing pipeline, persistence, and retrieval
│   ├── scripts/   Maintenance utilities (retrieval evaluation, collection reset)
│   └── tests/     Unit tests (hermetic) and an opt-in live end-to-end test
├── frontend/      React + Vite web application
├── DEPLOYMENT.md  Deployment checklist and environment configuration
└── README.md
```

## Requirements

- Python 3.11+ (production uses the version in `backend/runtime.txt`)
- Node.js 18+
- A PostgreSQL-compatible database
- Qdrant (hosted, or local embedded storage for development)
- A Gemini API key and a Cloudflare account with Workers AI access

## Local setup

### Backend

```bash
cd backend
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
# macOS/Linux
source venv/bin/activate
pip install -r requirements-dev.txt
```

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string. Tables are created/migrated automatically on startup. |
| `JWT_SECRET` | Secret used to sign login tokens. Use a long random value. |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini credentials and model used to answer questions. |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Workers AI credentials used for embeddings. |
| `QDRANT_URL`, `QDRANT_API_KEY` | Hosted Qdrant. If either is empty, vectors are stored locally in `backend/qdrant_data/`. |
| `FRONTEND_URL` | Extra allowed CORS origin (the deployed frontend). |

Then start the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8200
```

The API health endpoint is available at `http://127.0.0.1:8200/health`.

### Frontend

```bash
cd frontend
npm install
```

The frontend talks to `http://127.0.0.1:8200` by default. To use a different API, create `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8200
```

Start the development server:

```bash
npm run dev
```

Open the local URL shown by Vite, usually `http://localhost:5173`.

## Verification

Run frontend checks from `frontend/`:

```bash
npm run lint
npm test
npm run build
```

Run backend tests from `backend/` after activating the virtual environment:

```bash
python -m unittest discover -s tests
```

The backend unit tests are hermetic: they replace every credential with a dummy value and mock the database and providers, so they never touch the services configured in your `.env`. The opt-in live end-to-end test is described in [backend/tests/README.md](backend/tests/README.md).

## API overview

All routes except `/`, `/health`, and `/auth/*` require an `Authorization: Bearer <token>` header.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/register`, `/auth/login` | Create an account or log in; returns a token valid for 7 days. |
| `GET` | `/repositories` | List your indexed repositories. |
| `POST` | `/repositories/index` | Start (or join) an indexing job. Returns `202` with a `job_id`. |
| `GET` | `/repositories/index/{job_id}` | Poll the status of one of your indexing jobs. |
| `DELETE` | `/repositories/{repository_id}` | Delete a repository, its vectors, files, and chats. |
| `GET` | `/repositories/{repository_id}/files` | List indexed files. |
| `GET`, `POST` | `/repositories/{repository_id}/chats` | List or create chats for a repository. |
| `GET`, `DELETE` | `/chats/{chat_id}` | Load or delete a chat and its messages. |
| `POST` | `/ask` | Ask a question about a repository, optionally saving it to a chat. |

### Rate limits

Limits are counted in PostgreSQL, so they are shared by every backend process and survive restarts.

| Action | Limit |
| --- | --- |
| Login | 10 per email and 30 per IP address per 15 minutes |
| Register | 5 per IP address per 15 minutes |
| Index | 10 per user per minute |
| Ask | 30 per user per minute |

## Maintenance scripts

Run from `backend/` with the virtual environment active. Both use the real services in `.env`.

```bash
# Score retrieval quality for an indexed repository (edit the expected files in the script first)
python -m scripts.evaluate_retrieval <repository_id>

# Delete the entire Qdrant collection for ALL users (irreversible)
python -m scripts.reset_collection
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the production checklist, required environment variables, backend process command, and frontend build configuration.

For a deployed frontend, set:

```env
VITE_API_URL=https://your-api.example.com
```

The backend must allow the exact deployed frontend origin through `FRONTEND_URL`.

## Security notes

- Never commit `.env` files, API keys, database credentials, or Qdrant tokens.
- Keep provider credentials on the backend; only the public API URL belongs in the frontend environment.
- Use a strong, unique `JWT_SECRET` in every deployed environment.
- Repository source is untrusted input. Archives are extracted without symlinks or links, downloads are size- and time-limited, and repository content is passed to the model with instructions to ignore any embedded directives.
- Indexing errors shown to users are limited to messages written for them; internal provider errors are logged on the server only.

## License

Add the project license here before public distribution.
