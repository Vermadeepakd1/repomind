from app.embeddings import embed_text
from app.vector_db import search_vectors

from app.reranker import rerank_results
REPOSITORY_ID = "0ffe5461cac267ca"


tests = [
    {
        "question": "How is authentication implemented?",
        "expected": "authMiddleware.js",
    },
    {
        "question": "How are LeetCode statistics fetched?",
        "expected": "leetcodeService.js",
    },
    {
        "question": "How is the leaderboard calculated?",
        "expected": "leaderboardRoutes.js",
    },
    {
        "question": "How are daily coding statistics stored?",
        "expected": "DailyStat.js",
    },
    {
        "question": "How is user authentication state maintained on the frontend?",
        "expected": "AuthContext.jsx",
    },
]


for test in tests:

    question = test["question"]
    expected = test["expected"]

    query_vector = embed_text(question)

    results = search_vectors(
        query_vector,
        limit=20,
        repository_id=REPOSITORY_ID
    )

    results = rerank_results(
        question,
        results,
        limit=5
    )

    retrieved = [
        {
            "file": result.payload["file_path"],
            "chunk": result.payload["chunk_index"],
            "score": result.score,
        }
        for result in results
    ]

    files = [
        item["file"]
        for item in retrieved
    ]

    top_1 = any(
        expected in file
        for file in files[:1]
    )

    top_3 = any(
        expected in file
        for file in files[:3]
    )

    top_5 = any(
        expected in file
        for file in files[:5]
    )

    print("\n========================================")

    print("Question:")
    print(question)

    print("\nExpected:")
    print(expected)

    print("\nRetrieved:")

    for index, item in enumerate(retrieved):

        print(
            f"{index + 1}. "
            f"{item['file']} "
            f"(chunk {item['chunk']}, "
            f"score {item['score']:.3f})"
        )

    print("\nResults:")

    print(
        "Top-1:",
        "PASS" if top_1 else "FAIL"
    )

    print(
        "Top-3:",
        "PASS" if top_3 else "FAIL"
    )

    print(
        "Top-5:",
        "PASS" if top_5 else "FAIL"
    )