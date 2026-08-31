import re

def normalize_tokens(text: str) -> set[str]:
    text = text.lower()

    tokens = re.findall(
        r"[a-zA-Z0-9]+",
        text
    )

    return set(tokens)

def filename_score(
    question: str,
    file_path: str
) -> float:

    question_tokens = tokenize(question)

    filename = (
        file_path
        .replace("\\", "/")
        .split("/")[-1]
    )

    filename_tokens = tokenize(filename)

    if not filename_tokens:
        return 0.0

    matches = (
        question_tokens
        & filename_tokens
    )

    return min(
        len(matches) * 0.05,
        0.15
    )
    
def path_score(
    question: str,
    file_path: str
) -> float:

    question_tokens = tokenize(question)

    path_tokens = tokenize(file_path)

    if not path_tokens:
        return 0.0

    matches = (
        question_tokens
        & path_tokens
    )

    return min(
        len(matches) * 0.02,
        0.06
    )
    
def content_keyword_score(
    question: str,
    text: str
) -> float:

    question_tokens = normalize_tokens(
        question
    )

    text_tokens = normalize_tokens(
        text
    )

    if not question_tokens:
        return 0.0

    matches = (
        question_tokens
        & text_tokens
    )

    return min(
        len(matches) * 0.01,
        0.08
    )


def symbol_score(question: str, symbols: list[str]) -> float:
    if not symbols:
        return 0.0

    question_tokens = tokenize(question)
    symbol_tokens = set()
    for symbol in symbols:
        symbol_tokens.update(tokenize(symbol))

    return min(len(question_tokens & symbol_tokens) * 0.06, 0.18)

STOP_WORDS = {
    "how",
    "is",
    "are",
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "for",
    "does",
    "do",
    "what",
    "where",
    "and",
}


def tokenize(text: str):

    tokens = set()

    raw_tokens = re.findall(
        r"[a-zA-Z0-9_]+",
        text
    )

    for raw_token in raw_tokens:

        # Keep the complete token
        # Example: LeetCode -> leetcode
        full_token = raw_token.lower()

        if full_token not in STOP_WORDS:
            tokens.add(full_token)

        # Split camelCase / PascalCase
        split_token = re.sub(
            r"([a-z0-9])([A-Z])",
            r"\1 \2",
            raw_token
        )

        parts = split_token.split()

        for part in parts:

            part = part.lower()

            if part not in STOP_WORDS:
                tokens.add(part)

    return tokens

def rerank_results(
    question: str,
    results: list,
    limit: int = 5
):

    scored_results = []

    for result in results:

        payload = result.payload

        file_path = payload["file_path"]
        text = payload["text"]

        # --------------------------------
        # 1. Original semantic similarity
        # --------------------------------

        semantic_score = result.score

        # --------------------------------
        # 2. Generic filename relevance
        # --------------------------------

        filename_relevance = filename_score(
            question,
            file_path
        )

        # --------------------------------
        # 3. Generic path relevance
        # --------------------------------

        path_relevance = path_score(
            question,
            file_path
        )

        # --------------------------------
        # 4. Generic content relevance
        # --------------------------------

        content_relevance = content_keyword_score(
            question,
            text
        )

        symbol_relevance = symbol_score(
            question,
            payload.get("symbols", []),
        )

        # --------------------------------
        # 5. Final score
        # --------------------------------

        final_score = (
            semantic_score
            + filename_relevance
            + path_relevance
            + content_relevance
            + symbol_relevance
        )

        scored_results.append(
            (
                final_score,
                result
            )
        )

    # Highest score first
    scored_results.sort(
        key=lambda item: item[0],
        reverse=True
    )

    # --------------------------------
    # Diversification
    # --------------------------------

    selected = []

    seen_files = set()

    # First pass:
    # Prefer different files
    for score, result in scored_results:

        file_path = result.payload["file_path"]

        if file_path in seen_files:
            continue

        selected.append(result)
        seen_files.add(file_path)

        if len(selected) == limit:
            break

    # Second pass:
    # Allow additional chunks if necessary
    if len(selected) < limit:

        for score, result in scored_results:

            if result in selected:
                continue

            selected.append(result)

            if len(selected) == limit:
                break

    return selected
