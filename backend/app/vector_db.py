import os
import hashlib

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

load_dotenv()


QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


if QDRANT_URL and QDRANT_API_KEY:

    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )

else:

    client = QdrantClient(
        path="./qdrant_data"
    )


COLLECTION_NAME = "repository_code"


def create_collection(vector_size: int):

    if client.collection_exists(
        COLLECTION_NAME
    ):
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="repository_id",
        field_schema="keyword",
    )


def add_chunks(chunks: list):
    if not chunks:
        return

    vector_size = len(
        chunks[0]["vector"]
    )

    create_collection(vector_size)

    points = []

    for chunk in chunks:
        point_id = hashlib.md5(
            f"{chunk['repository_id']}:{chunk['file_path']}:{chunk['chunk_index']}".encode()
        ).hexdigest()

        points.append(
            PointStruct(
                id=point_id,
                vector=chunk["vector"],
                payload={
                    "repository_id": chunk["repository_id"],
                    "file_path": chunk["file_path"],
                    "chunk_index": chunk["chunk_index"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "text": chunk["text"],
                },
            )
        )

    # Upload in smaller batches instead of one large request.
    batch_size = 50

    for start in range(0, len(points), batch_size):
        batch = points[start:start + batch_size]

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
            wait=True,
        )

def search_vectors(
    query_vector: list,
    repository_id: str,
    limit: int = 5
):

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="repository_id",
                    match=MatchValue(
                        value=repository_id
                    ),
                )
            ]
        ),
        limit=limit,
    )

    return results.points


def delete_repository_chunks(
    repository_id: str
):

    if not client.collection_exists(
        COLLECTION_NAME
    ):
        return

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="repository_id",
                    match=MatchValue(
                        value=repository_id
                    )
                )
            ]
        ),
        wait=True,
    )