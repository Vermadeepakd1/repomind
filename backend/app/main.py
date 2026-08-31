import json
import logging
import time
from uuid import uuid4

import os

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

from app.context_builder import build_context
from app.conversation import build_retrieval_question
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.embeddings import embed_text
from app.github import cleanup_repository, clone_repository, get_code_files
from app.index_jobs import (
    create_job,
    get_job,
    mark_unfinished_jobs_failed,
    update_job,
)
from app.indexer import index_repository
from app.llm import ask_gemini
from app.repository import get_repository_id
from app.repository_store import (
    create_user,
    get_repositories,
    add_chat_message,
    create_chat,
    get_chat,
    get_chat_messages,
    get_chats,
    get_repository_files,
    get_user_by_email,
    init_database,
    repository_belongs_to_user,
    save_repository,
    save_repository_files,
)
from app.reranker import rerank_results
from app.rate_limit import check_rate_limit
from app.schemas import AskRequest, AuthRequest, RepositoryRequest
from app.vector_db import delete_repository_chunks, search_vectors


app = FastAPI(title="RepoMind API")
init_database()
mark_unfinished_jobs_failed()
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

logger = logging.getLogger("repomind.api")


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


@app.get("/")
def root():
    return {"message": "RepoMind API is running!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def register(request: AuthRequest):
    if get_user_by_email(request.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = create_user(request.email, hash_password(request.password))
    return {"token": create_access_token(user["user_id"]), "user": user}


@app.post("/auth/login")
def login(request: AuthRequest):
    user = get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    public_user = {"user_id": user["user_id"], "email": user["email"]}
    return {"token": create_access_token(user["user_id"]), "user": public_user}


@app.post("/repositories/analyze")
def analyze_repository(request: RepositoryRequest, current_user=Depends(get_current_user)):
    repo_path = None

    try:
        repo_path = clone_repository(request.repo_url)
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
    repository_id = get_repository_id(request.repo_url, user_id)
    repo_path = None

    try:
        update_job(job_id, status="running", stage="Cloning repository")
        repo_path = clone_repository(request.repo_url)

        update_job(job_id, stage="Reading source files")
        files = get_code_files(repo_path)
        if not files:
            raise ValueError("No readable source files were found in the repository.")

        delete_repository_chunks(repository_id)
        update_job(job_id, stage="Embedding and storing source code")
        chunk_count = index_repository(files, repository_id)

        repo_name = request.repo_url.rstrip("/").split("/")[-1]
        save_repository_files(repository_id, user_id, files)
        save_repository(
            repository_id=repository_id,
            repo_url=request.repo_url,
            repo_name=repo_name,
            chunk_count=chunk_count,
            user_id=user_id,
        )
        update_job(
            job_id,
            status="completed",
            stage="Indexing complete",
            chunk_count=chunk_count,
        )
    except Exception as error:
        print("Indexing error:", error)
        try:
            delete_repository_chunks(repository_id)
        except Exception as cleanup_error:
            print("Index cleanup error:", cleanup_error)
        update_job(
            job_id,
            status="failed",
            stage="Indexing failed",
            error=str(error) or "Repository indexing failed before completion.",
        )
    finally:
        if repo_path:
            cleanup_repository(repo_path)


@app.post("/repositories/index", status_code=202)
def index_repository_endpoint(
    request: RepositoryRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    user_id = current_user["user_id"]
    if not check_rate_limit(f"index:{user_id}", limit=10):
        raise HTTPException(status_code=429, detail="Indexing rate limit reached. Please try again later.")
    repository_id = get_repository_id(request.repo_url, user_id)
    job = create_job(repository_id)
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
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Indexing job was not found. It may have expired or run on another server.",
        )
    return job


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


@app.get("/repositories/{repository_id}/files")
def list_repository_files(repository_id: str, current_user=Depends(get_current_user)):
    if not repository_belongs_to_user(repository_id, current_user["user_id"]):
        raise HTTPException(status_code=404, detail="Repository was not found.")
    return {"files": get_repository_files(repository_id, current_user["user_id"])}


@app.post("/ask")
def ask_repository(request: AskRequest, current_user=Depends(get_current_user)):
    try:
        if not check_rate_limit(f"ask:{current_user['user_id']}", limit=30):
            raise HTTPException(status_code=429, detail="Question rate limit reached. Please try again later.")

        repository_id = get_repository_id(request.repo_url, current_user["user_id"])
        if request.chat_id:
            chat = get_chat(request.chat_id, current_user["user_id"])
            if not chat or chat["repository_id"] != repository_id:
                raise HTTPException(status_code=404, detail="Chat was not found.")

        retrieval_question = build_retrieval_question(
            request.question,
            request.conversation,
        )

        query_vector = embed_text(retrieval_question)
        candidates = search_vectors(query_vector, repository_id, limit=20)
        results = rerank_results(request.question, candidates, limit=5)
        if not results:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No indexed repository data found. "
                    "Please index the repository first."
                ),
            )

        answer = ask_gemini(
            request.question,
            build_context(results),
            [message.model_dump() for message in request.conversation],
        )
        if request.chat_id:
            add_chat_message(request.chat_id, "user", request.question)
            add_chat_message(
                request.chat_id,
                "assistant",
                answer,
                [
                    {
                        "file": result.payload["file_path"],
                        "chunk": result.payload["chunk_index"],
                        "start_line": result.payload["start_line"],
                        "end_line": result.payload["end_line"],
                        "score": result.score,
                    }
                    for result in results
                ],
            )
        return {
            "question": request.question,
            "repository_id": repository_id,
            "answer": answer,
            "sources": [
                {
                    "file": result.payload["file_path"],
                    "chunk": result.payload["chunk_index"],
                    "start_line": result.payload["start_line"],
                    "end_line": result.payload["end_line"],
                    "score": result.score,
                }
                for result in results
            ],
        }
    except HTTPException:
        raise
    except Exception as error:
        print("Ask error:", error)
        raise HTTPException(
            status_code=500,
            detail="Unable to process repository question.",
        )


@app.get("/repositories")
def list_indexed_repositories(current_user=Depends(get_current_user)):
    return {"repositories": get_repositories(current_user["user_id"])}
