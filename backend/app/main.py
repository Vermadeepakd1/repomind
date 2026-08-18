from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.github import (
    clone_repository,
    get_code_files,
    cleanup_repository
)
from app.llm import ask_gemini
from app.indexer import index_repository
from app.vector_db import (
    search_vectors,
    delete_repository_chunks,
)
from app.embeddings import embed_text
from app.context_builder import build_context
from app.repository import get_repository_id


from app.repository_store import (
    init_database,
    save_repository,
    get_repositories,
    get_repository,
)


app = FastAPI(title="RepoMind API")
init_database()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://repomind-omega.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RepositoryRequest(BaseModel):
    repo_url: str


class ConversationMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    repo_url: str
    question: str
    conversation: list[ConversationMessage] = []


@app.get("/")
def root():

    return {
        "message": "RepoMind API is running!"
    }


@app.post("/repositories/analyze")
def analyze_repository(
    request: RepositoryRequest
):

    repo_path = None

    try:
        repo_path = clone_repository(
            request.repo_url
        )

        files = get_code_files(repo_path)

        if not files:
            raise HTTPException(
                status_code=400,
                detail="No readable source files were found in the repository."
            )

        return {
            "file_count": len(files),
            "files": files[:10]
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    finally:
        if repo_path:
            cleanup_repository(repo_path)

@app.post("/repositories/index")
def index_repository_endpoint(
    request: RepositoryRequest
):

    repo_path = None

    try:
        repo_path = clone_repository(
            request.repo_url
        )

        files = get_code_files(repo_path)

        if not files:
            raise HTTPException(
                status_code=400,
                detail="No readable source files were found in the repository."
            )

        repository_id = get_repository_id(
            request.repo_url
        )

        delete_repository_chunks(
            repository_id
        )

        chunk_count = index_repository(
            files,
            repository_id
        )
        
        repo_name = request.repo_url.rstrip("/").split("/")[-1]

        save_repository(
            repository_id=repository_id,
            repo_url=request.repo_url,
            repo_name=repo_name,
            chunk_count=chunk_count,
        )

        return {
            "message": "Repository indexed successfully",
            "repository_id": repository_id,
            "chunk_count": chunk_count
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    finally:
        if repo_path:
            cleanup_repository(repo_path)


@app.post("/ask")
def ask_repository(request: AskRequest):

    try:
        repository_id = get_repository_id(
            request.repo_url
        )

        retrieval_question = request.question

        if request.conversation:
            previous_user_messages = [
                message.content
                for message in request.conversation
                if message.role == "user"
            ]

            if previous_user_messages:
                retrieval_question = (
                    previous_user_messages[-1]
                    + "\n"
                    + request.question
                )

        query_vector = embed_text(
            retrieval_question
        )

        results = search_vectors(
            query_vector,
            repository_id,
            limit=5
        )

        if not results:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No indexed repository data found. "
                    "Please index the repository first."
                )
            )

        context = build_context(results)

        answer = ask_gemini(
            request.question,
            context,
            [
                {
                    "role": message.role,
                    "content": message.content
                }
                for message in request.conversation
            ]
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
                    "score": result.score
                }
                for result in results
            ]
        }

    except HTTPException:
        raise

    except Exception as error:
        print("Ask error:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to process repository question."
        )
        
@app.get("/repositories")
def list_indexed_repositories():

    return {
        "repositories": get_repositories()
    }