from app.llm import embed_texts


texts = [
    "JWT authentication verifies a user's identity.",
    "React is used to build the frontend interface.",
    "PostgreSQL stores relational application data.",
    "Redis can be used for caching.",
]


vectors = embed_texts(texts)

print("Number of vectors:", len(vectors))

for i, vector in enumerate(vectors):
    print(
        f"Text {i + 1}: "
        f"vector length = {len(vector)}"
    )