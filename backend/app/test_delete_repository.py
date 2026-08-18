from app.vector_db import (
    delete_repository_chunks,
    search_vectors,
)
from app.embeddings import embed_text


REPOSITORY_ID = "78af1611233cd6a9"

query_vector = embed_text(
    "How is authentication implemented?"
)

before = search_vectors(
    query_vector,
    REPOSITORY_ID,
    limit=5
)

print("Results before deletion:", len(before))

delete_repository_chunks(
    REPOSITORY_ID
)

after = search_vectors(
    query_vector,
    REPOSITORY_ID,
    limit=5
)

print("Results after deletion:", len(after))