from app.chunking import chunk_text
from app.code_metadata import extract_symbols
from app.embeddings import embed_texts
from app.vector_db import add_chunks


def index_repository(
    files: list,
    repository_id: str
):
    # Larger embedding batches reduce provider round trips while staying
    # small enough for the embedding API request limits.
    batch_size = 20
    total_chunks = 0
    pending_chunks = []

    # Process files one at a time
    for file in files:
        chunks = chunk_text(file["content"])

        for index, chunk in enumerate(chunks):
            pending_chunks.append({
                "repository_id": repository_id,
                "file_path": file["path"],
                "chunk_index": index,
                "text": chunk["text"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "symbols": extract_symbols(chunk["text"]),
            })

            # Once we have a batch, embed and store it
            if len(pending_chunks) >= batch_size:
                total_chunks = _process_batch(
                    pending_chunks,
                    total_chunks
                )
                pending_chunks = []

    # Process remaining chunks
    if pending_chunks:
        total_chunks = _process_batch(
            pending_chunks,
            total_chunks
        )

    return total_chunks


def _process_batch(
    chunks: list,
    total_chunks: int
):
    batch_texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print(
        f"Embedding chunks "
        f"{total_chunks + 1}-"
        f"{total_chunks + len(chunks)}"
    )

    vectors = embed_texts(batch_texts)

    for chunk, vector in zip(
        chunks,
        vectors
    ):
        chunk["vector"] = vector

    # Store this batch immediately
    add_chunks(chunks)

    total_chunks += len(chunks)

    print(
        f"Stored {total_chunks} chunks"
    )

    return total_chunks
