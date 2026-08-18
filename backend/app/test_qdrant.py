from app.embeddings import embed_texts
from app.vector_db import (
    add_chunks,
    search_vectors
)


texts = [
    "JWT authentication verifies user tokens.",
    "React components render the user interface.",
    "PostgreSQL stores application data.",
]


vectors = embed_texts(texts)


chunks = []

for i, (text, vector) in enumerate(
    zip(texts, vectors)
):

    chunks.append({
        "file_path": f"test_file_{i}.txt",
        "chunk_index": 0,
        "text": text,
        "vector": vector,
    })


add_chunks(chunks)


query = "How does user authentication work?"

query_vector = embed_texts(
    [query]
)[0]


results = search_vectors(
    query_vector,
    limit=2
)


for result in results:

    print(
        "\nFile:",
        result.payload["file_path"]
    )

    print(
        "Text:",
        result.payload["text"]
    )

    print(
        "Score:",
        result.score
    )