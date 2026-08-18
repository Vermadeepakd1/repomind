from app.llm import embed_text


vector = embed_text(
    "JWT authentication verifies a user's identity."
)

print("Vector length:", len(vector))
print("First 10 values:", vector[:10])