from app.vector_db import search_vectors
from app.embeddings import embed_text


query = "How does authentication work?"

vector = embed_text(query)

results = search_vectors(
    vector,
    limit=3,
    repository_id="test-repository"
)


for result in results:

    print("\n--------------------")

    print(
        "File:",
        result.payload["file_path"]
    )

    print(
        "Chunk:",
        result.payload["chunk_index"]
    )

    print(
        "Lines:",
        result.payload["start_line"],
        "-",
        result.payload["end_line"]
    )

    print(
        "Score:",
        result.score
    )

    print(
        "Text:",
        result.payload["text"]
    )