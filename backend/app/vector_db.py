import hashlib
import os
from functools import lru_cache

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.reliability import retry_call

load_dotenv()


COLLECTION_NAME = "repository_code"
KEYWORD_FIELDS = ("repository_id", "index_version")


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if url and api_key:
        return QdrantClient(url=url, api_key=api_key, timeout=30)
    return QdrantClient(path="./qdrant_data")


_collection_ready = False


def create_collection(vector_size: int):
    global _collection_ready
    if _collection_ready:
        return

    client = get_client()
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

    # Creating an existing payload index is a no-op, so this also upgrades
    # collections created before index versions were introduced.
    for field_name in KEYWORD_FIELDS:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema="keyword",
        )

    _collection_ready = True


def _point_id(chunk: dict) -> str:
    identity = (
        f"{chunk['repository_id']}:{chunk.get('index_version') or ''}:"
        f"{chunk['file_path']}:{chunk['chunk_index']}"
    )
    return hashlib.md5(identity.encode()).hexdigest()


def add_chunks(chunks: list):
    if not chunks:
        return

    create_collection(len(chunks[0]["vector"]))

    points = [
        PointStruct(
            id=_point_id(chunk),
            vector=chunk["vector"],
            payload={
                "repository_id": chunk["repository_id"],
                "index_version": chunk.get("index_version"),
                "file_path": chunk["file_path"],
                "chunk_index": chunk["chunk_index"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "symbols": chunk.get("symbols", []),
                "text": chunk["text"],
            },
        )
        for chunk in chunks
    ]

    # Upload in smaller batches instead of one large request.
    batch_size = 50
    client = get_client()

    for start in range(0, len(points), batch_size):
        batch = points[start:start + batch_size]

        retry_call(
            lambda batch=batch: client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch,
                wait=True,
            ),
            operation_name="Qdrant upsert",
        )


def _repository_filter(
    repository_id: str,
    index_version: str | None = None,
    exclude_version: str | None = None,
) -> Filter:
    must = [
        FieldCondition(key="repository_id", match=MatchValue(value=repository_id))
    ]
    if index_version:
        must.append(
            FieldCondition(key="index_version", match=MatchValue(value=index_version))
        )
    must_not = []
    if exclude_version:
        must_not.append(
            FieldCondition(key="index_version", match=MatchValue(value=exclude_version))
        )
    return Filter(must=must, must_not=must_not or None)


def search_vectors(
    query_vector: list,
    repository_id: str,
    limit: int = 5,
    index_version: str | None = None,
):
    """Search one repository, restricted to its active index version if known.

    Repositories indexed before versioning have no ``index_version``; they are
    searched by repository only.
    """
    client = get_client()
    if not client.collection_exists(COLLECTION_NAME):
        return []

    results = retry_call(
        lambda: client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=_repository_filter(repository_id, index_version),
            limit=limit,
        ),
        operation_name="Qdrant search",
    )

    return results.points


def delete_repository_chunks(
    repository_id: str,
    index_version: str | None = None,
    exclude_version: str | None = None,
):
    """Delete a repository's chunks.

    ``index_version`` limits deletion to one version (e.g. a failed build);
    ``exclude_version`` deletes everything except that version (e.g. stale
    chunks after a successful reindex). With neither, all chunks are removed.
    """
    client = get_client()
    if not client.collection_exists(COLLECTION_NAME):
        return

    retry_call(
        lambda: client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=_repository_filter(
                repository_id, index_version, exclude_version
            ),
            wait=True,
        ),
        operation_name="Qdrant delete",
    )
