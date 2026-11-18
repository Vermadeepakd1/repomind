# RepoMind frontend

React + Vite web app for RepoMind. See the [root README](../README.md) for full setup.

```bash
npm install
npm run dev      # start the dev server (http://localhost:5173)
npm run lint
npm test         # node --test over src/utils/*.test.js
npm run build
```

The API URL defaults to `http://127.0.0.1:8200`; override it with `VITE_API_URL` in `frontend/.env`.

## Layout

- `src/api.js` – API client. All requests go through one helper that signs the user out when a stored token is rejected (`401`).
- `src/App.jsx` – app state: auth, repositories, indexing, chats.
- `src/components/` – views (landing, auth, repository list, chat).
- `src/utils/pollIndexJob.js` – indexing status polling with a timeout, retries for transient errors, and cancellation on logout.
- `src/utils/repositoryUrl.js` – GitHub URL normalisation used to detect duplicates.
