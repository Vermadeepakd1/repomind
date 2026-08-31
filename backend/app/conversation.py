import re


FOLLOW_UP_PHRASES = {
    "it",
    "this",
    "that",
    "these",
    "those",
    "they",
    "them",
    "there",
    "here",
    "also",
    "instead",
}


def build_retrieval_question(question: str, conversation: list) -> str:
    """Add recent context when a question is likely a follow-up."""
    normalized = question.lower()
    tokens = set(re.findall(r"[a-z0-9_]+", normalized))
    is_follow_up = (
        len(tokens) <= 12
        or bool(tokens & FOLLOW_UP_PHRASES)
        or normalized.startswith(("and ", "what about ", "how about ", "where else "))
    )

    if not conversation or not is_follow_up:
        return question

    recent_messages = conversation[-6:]
    context = "\n".join(
        f"{message.role}: {message.content}"
        for message in recent_messages
    )
    return f"Recent conversation:\n{context}\n\nFollow-up question:\n{question}"[-8000:]
