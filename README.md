# RepoMind

RepoMind is an AI-powered workspace for understanding public GitHub repositories. Index a repository, ask questions in plain language, and get answers grounded in the code with source references.

## What it does

- Indexes public GitHub repositories in the background.
- Splits source into searchable code chunks and stores embeddings in Qdrant.
- Uses Gemini to answer questions from the most relevant repository context.
- Supports persistent accounts, repositories, chat sessions, and message history.
- Provides repository metadata, file browsing, reindexing, retry handling, and health checks.

RepoMind currently supports public repositories only. It does not request or store GitHub credentials.

## Project structure

```text
repomind/
├── backend/       FastAPI API, indexing pipeline, persistence, and retrieval
├── frontend/      React + Vite web application
├── DEPLOYMENT.md  Deployment checklist and environment configuration
└── README.md
```

## Requirements

- Python 3.11+
- Node.js 18+
- A PostgreSQL-compatible database
- Qdrant (local or hosted)
- Gemini API access

## Local setup

### Backend

```bash
cd backend
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

Copy `backend/.env.example` to `backend/.env` and configure the database, JWT, Gemini, Qdrant, and CORS values. Then start the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8200
```

The API health endpoint is available at `http://127.0.0.1:8200/health`.

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

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
pytest
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
- Public repository source is cloned for indexing and should be treated as untrusted input.

## License

Add the project license here before public distribution.
