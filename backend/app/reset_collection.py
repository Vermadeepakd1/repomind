from app.vector_db import client, COLLECTION_NAME


if client.collection_exists(COLLECTION_NAME):
    client.delete_collection(
        collection_name=COLLECTION_NAME
    )

    print(
        f"Deleted collection: {COLLECTION_NAME}"
    )

else:
    print(
        f"Collection does not exist: {COLLECTION_NAME}"
    )