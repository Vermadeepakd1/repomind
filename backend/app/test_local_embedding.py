from app.embeddings import embed_texts


texts = [
    "JWT authentication verifies user tokens.",
    "The application validates authentication tokens.",
    "React renders components on the frontend.",
    "The database stores user records."
]


vectors = embed_texts(texts)


print("Number of vectors:", len(vectors))

for i, vector in enumerate(vectors):

    print(
        f"Text {i + 1}: "
        f"Vector length = {len(vector)}"
    )