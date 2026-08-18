from app.embeddings import embed_text
from app.vector_db import search_vectors
from app.reranker import rerank_results


REPOSITORY_ID = "0ffe5461cac267ca"

question = "How are LeetCode statistics fetched?"
expected = "leetcodeService.js"


query_vector = embed_text(
    question
)


results = search_vectors(
    query_vector,
    limit=20,
    repository_id=REPOSITORY_ID
)


print("\nOriginal Top 20:")

for index, result in enumerate(results):

    print(
        f"{index + 1}. "
        f"{result.payload['file_path']} "
        f"(chunk {result.payload['chunk_index']}, "
        f"score {result.score:.3f})"
    )


expected_rank = None

for index, result in enumerate(results):

    file_path = result.payload["file_path"]

    if expected in file_path:
        expected_rank = index + 1
        break


print("\nExpected file:")

print(expected)


if expected_rank:
    print(
        f"Found at original rank: "
        f"{expected_rank}"
    )
else:
    print(
        "Expected file was NOT found "
        "in the top 20 candidates."
    )


reranked = rerank_results(
    question,
    results,
    limit=5
)


print("\nReranked Top 5:")

for index, result in enumerate(reranked):

    print(
        f"{index + 1}. "
        f"{result.payload['file_path']} "
        f"(chunk {result.payload['chunk_index']}, "
        f"score {result.score:.3f})"
    )