from sentence_transformers import SentenceTransformer


model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def embed_text(text: str):

    vector = model.encode(
        text,
        normalize_embeddings=True
    )

    return vector.tolist()


def embed_texts(texts: list[str]):

    vectors = model.encode(
        texts,
        normalize_embeddings=True
    )

    return vectors.tolist()