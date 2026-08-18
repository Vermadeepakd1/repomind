from app.vector_db import client, COLLECTION_NAME


info = client.get_collection(
    collection_name=COLLECTION_NAME
)

print("Collection:", COLLECTION_NAME)
print("Points:", info.points_count)