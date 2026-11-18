import json
import logging
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.context_builder import build_context
from app.conversation import build_retrieval_question
from app.embeddings import embed_text
from app.github import cleanup_repository, download_repository, get_code_files
from app.index_jobs import (
    create_job,
    get_job,
    mark_unfinished_jobs_failed,
    update_job,
)
from app.indexer import index_repository
from app.llm import ask_gemini
from app.rate_limit import check_rate_limit
from app.repository import get_repository_id
from app.repository_store import (
    add_chat_exchange,
    create_chat,
    create_user,
    delete_chat,
    delete_repository,
    get_chat,
    get_chat_messages,
    get_chats,
    get_repositories,
    get_repository,
    get_repository_files,
    get_user_by_email,
    init_database,
    repository_belongs_to_user,
    save_repository,
    save_repository_files,
)
from app.reranker import rerank_results
from app.schemas import AskRequest, AuthRequest, RepositoryRequest
from app.vector_db import delete_repository_chunks, search_vectors


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repomind.api")

# Login: per-account limit stops password guessing even if the attacker
# rotates IP addresses; per-IP limits stop spraying many accounts.
LOGIN_LIMIT_PER_EMAIL = 10
LOGIN_LIMIT_PER_IP = 30
REGISTER_LIMIT_PER_IP = 5
AUTH_WINDOW_SECONDS = 15 * 60

GENERIC_INDEX_ERROR = "Repository indexing failed. Please try again."


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_database()
    mark_unfinished_jobs_failed()
    yield


app = FastAPI(title="RepoMind API", lifespan=lifespan)
frontend_url = os.getenv("FRONTEND_URL")
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://repomind-omega.vercel.app",
]
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid4())
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            json.dumps({
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": 500,
            })
        )
        raise

    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        })
    )
    return response


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(key: str, limit: int, window_seconds: int, message: str):
    if not check_rate_limit(key, limit=limit, window_seconds=window_seconds):
        raise HTTPException(status_code=429, detail=message)


@app.get("/")
def root():
    return {"message": "RepoMind API is running!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def register(request: AuthRequest, http_request: Request):
    _enforce_rate_limit(
        f"register:ip:{_client_ip(http_request)}",
        REGISTER_LIMIT_PER_IP,
        AUTH_WINDOW_SECONDS,
        "Too many sign-up attempts. Please try again later.",
    )
    if get_user_by_email(request.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = create_user(request.email, hash_password(request.password))
    return {"token": create_access_token(user["user_id"]), "user": user}


@app.post("/auth/login")
def login(request: AuthRequest, http_request: Request):
    message = "Too many login attempts. Please try again later."
    _enforce_rate_limit(
        f"login:ip:{_client_ip(http_request)}",
        LOGIN_LIMIT_PER_IP,
        AUTH_WINDOW_SECONDS,
        message,
    )
    _enforce_rate_limit(
        f"login:email:{request.email}",
        LOGIN_LIMIT_PER_EMAIL,
        AUTH_WINDOW_SECONDS,
        message,
    )

    user = get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    public_user = {"user_id": user["user_id"], "email": user["email"]}
    return {"token": create_access_token(user["user_id"]), "user": public_user}


@app.post("/repositories/analyze")
def analyze_repository(request: RepositoryRequest, current_user=Depends(get_current_user)):
    repo_path = None

    try:
        repo_path = download_repository(request.repo_url)
        files = get_code_files(repo_path)
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No readable source files were found in the repository.",
            )
        return {"file_count": len(files), "files": files[:10]}
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    finally:
        if repo_path:
            cleanup_repository(repo_path)


def _run_index_job(job_id: str, request: RepositoryRequest, user_id: str):
    """Build a new index version and swap it in only once it is complete.

    Chunks are written under ``index_version = job_id`` alongside the
    previous version, so questions keep using the old index while a reindex
    runs, and a failed reindex leaves the old index untouched.
    """
    repository_id = get_repository_id(request.repo_url, user_id)
    index_version = job_id
    repo_path = None

    try:
        update_job(job_id, status="running", stage="Downloading repository")
        repo_path = download_repository(request.repo_url)

        update_job(job_id, stage="Reading source files")
        files = get_code_files(repo_path)
        if not files:
            raise ValueError("No readable source files were found in the repository.")

        update_job(job_id, stage="Embedding and storing source code")
        chunk_count = index_repository(files, repository_id, index_version)

        repo_name = request.repo_url.rstrip("/").split("/")[-1]
        save_repository_files(repository_id, user_id, files)
        save_repository(
            repository_id=repository_id,
            repo_url=request.repo_url,
            repo_name=repo_name,
            chunk_count=chunk_count,
            user_id=user_id,
            index_version=index_version,
        )
    except Exception as error:
        logger.exception("Indexing job %s failed", job_id)
        try:
            delete_repository_chunks(repository_id, index_version=index_version)
        except Exception:
            logger.exception("Cleanup of failed index version %s failed", index_version)
        # ValueErrors carry messages written for users; anything else may
        # contain internal details, so it is replaced with a generic message.
        message = str(error) if isinstance(error, ValueError) and str(error) else GENERIC_INDEX_ERROR
        update_job(job_id, status="failed", stage="Indexing failed", error=message)
        return
    finally:
        if repo_path:
            cleanup_repository(repo_path)

    # The new version is live; stale chunks from earlier versions can go.
    try:
        delete_repository_chunks(repository_id, exclude_version=index_version)
    except Exception:
        logger.exception("Removing stale chunks for %s failed", repository_id)

    update_job(
        job_id,
        status="completed",
        stage="Indexing complete",
        chunk_count=chunk_count,
    )


@app.post("/repositories/index", status_code=202)
def index_repository_endpoint(
    request: RepositoryRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    user_id = current_user["user_id"]
    _enforce_rate_limit(
        f"index:{user_id}", 10, 60,
        "Indexing rate limit reached. Please try again later.",
    )
    repository_id = get_repository_id(request.repo_url, user_id)
    job = create_job(repository_id, user_id)
    if job["status"] == "queued":
        background_tasks.add_task(_run_index_job, job["job_id"], request, user_id)

    return {
        "message": "Repository indexing started",
        "job_id": job["job_id"],
        "repository_id": repository_id,
        "status": job["status"],
    }


@app.get("/repositories/index/{job_id}")
def get_index_job(job_id: str, current_user=Depends(get_current_user)):
    job = get_job(job_id, current_user["user_id"])
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Indexing job was not found. It may have expired or run on another server.",
        )
    return job


@app.delete("/repositories/{repository_id}", status_code=204)
def delete_repository_endpoint(repository_id: str, current_user=Depends(get_current_user)):
    if not delete_repository(repository_id, current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Repository was not found.")
    try:
        delete_repository_chunks(repository_id)
    except Exception:
        # The database records are gone, so the orphaned vectors are
        # unreachable; log for cleanup rather than failing the request.
        logger.exception("Deleting vectors for repository %s failed", repository_id)
    return Response(status_code=204)


@app.post("/repositories/{repository_id}/chats")
def create_repository_chat(repository_id: str, current_user=Depends(get_current_user)):
    if not repository_belongs_to_user(repository_id, current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Repository was not found.")
    return create_chat(current_user["user_id"], repository_id)


@app.get("/repositories/{repository_id}/chats")
def list_repository_chats(repository_id: str, current_user=Depends(get_current_user)):
    if not repository_belongs_to_user(repository_id, current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Repository was not found.")
    return {"chats": get_chats(current_user["user_id"], repository_id)}


@app.get("/chats/{chat_id}")
def get_chat_history(chat_id: str, current_user=Depends(get_current_user)):
    chat = get_chat(chat_id, current_user["user_id"])
    if not chat:
        raise HTTPException(status_code=404, detail="Chat was not found.")
    return {**chat, "messages": get_chat_messages(chat_id, current_user["user_id"])}


@app.delete("/chats/{chat_id}", status_code=204)
def delete_chat_endpoint(chat_id: str, current_user=Depends(get_current_user)):
    if not delete_chat(chat_id, current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Chat was not found.")
    return Response(status_code=204)


@app.get("/repositories/{repository_id}/files")
def list_repository_files(repository_id: str, current_user=Depends(get_current_user)):
    if not repository_belongs_to_user(repository_id, current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Repository was not found.")
    return {"files": get_repository_files(repository_id, current_user["user_id"])}


def _format_sources(results: list) -> list:
    return [
        {
            "file": result.payload["file_path"],
            "chunk": result.payload["chunk_index"],
            "start_line": result.payload["start_line"],
            "end_line": result.payload["end_line"],
            "score": result.score,
        }
        for result in results
    ]


@app.post("/ask")
def ask_repository(request: AskRequest, current_user=Depends(get_current_user)):
    user_id = current_user["user_id"]
    _enforce_rate_limit(
        f"ask:{user_id}", 30, 60,
        "Question rate limit reached. Please try again later.",
    )

    repository_id = get_repository_id(request.repo_url, user_id)
    repository = get_repository(repository_id, user_id)
    if not repository:
        raise HTTPException(
            status_code=404,
            detail="No indexed repository data found. Please index the repository first.",
        )

    if request.chat_id:
        chat = get_chat(request.chat_id, user_id)
        if not chat or chat["repository_id"] != repository_id:
            raise HTTPException(status_code=404, detail="Chat was not found.")

    try:
        retrieval_question = build_retrieval_question(
            request.question,
            request.conversation,
        )

        query_vector = embed_text(retrieval_question)
        candidates = search_vectors(
            query_vector,
            repository_id,
            limit=20,
            index_version=repository["index_version"],
        )
        results = rerank_results(request.question, candidates, limit=5)
        if not results:
            raise HTTPException(
                status_code=404,
                detail="No indexed repository data found. Please index the repository first.",
            )

        answer = ask_gemini(
            request.question,
            build_context(results),
            [message.model_dump() for message in request.conversation],
        )
        sources = _format_sources(results)
        if request.chat_id:
            add_chat_exchange(request.chat_id, request.question, answer, sources)
        return {
            "question": request.question,
            "repository_id": repository_id,
            "answer": answer,
            "sources": sources,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Ask failed for repository %s", repository_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to process repository question.",
        )


@app.get("/repositories")
def list_indexed_repositories(current_user=Depends(get_current_user)):
    return {"repositories": get_repositories(current_user["user_id"])}
