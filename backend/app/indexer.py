from app.chunking import chunk_text
from app.embeddings import embed_texts
from app.vector_db import add_chunks


def index_repository(
    files: list,
    repository_id: str
):

    all_chunks = []

    # Create chunks
    for file in files:

        chunks = chunk_text(
            file["content"]
        )

        for index, chunk in enumerate(chunks):
            all_chunks.append({
                "repository_id": repository_id,
                "file_path": file["path"],
                "chunk_index": index,
                "text": chunk["text"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
            })

    if not all_chunks:
        return 0

    # Generate embeddings in batches
    batch_size = 50

    for start in range(
        0,
        len(all_chunks),
        batch_size
    ):

        batch = all_chunks[
            start:start + batch_size
        ]

        batch_texts = [
            chunk["text"]
            for chunk in batch
        ]

        vectors = embed_texts(
            batch_texts
        )

        for chunk, vector in zip(
            batch,
            vectors
        ):

            chunk["vector"] = vector

    # Store vectors in Qdrant
    add_chunks(all_chunks)

    return len(all_chunks)