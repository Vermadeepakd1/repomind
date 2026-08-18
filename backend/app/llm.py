import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL")


if not api_key:
    raise ValueError(
        "GEMINI_API_KEY is not set"
    )

if not model_name:
    raise ValueError(
        "GEMINI_MODEL is not set"
    )


client = genai.Client(
    api_key=api_key
)


def ask_gemini(
    question: str,
    context: str,
    conversation: list | None = None
):

    conversation_text = ""

    if conversation:
        conversation_text = "\n\n".join(
            [
                f"{message['role'].upper()}: {message['content']}"
                for message in conversation
            ]
        )

    prompt = f"""
You are an expert software engineer helping the user understand a software repository.

Answer the user's question using the provided repository context and, when useful, the previous conversation.

Important rules:
- Use repository context as the source of truth for code-specific claims.
- Do not invent files, functions, or implementation details.
- If the repository context does not contain enough information, say so.
- Use previous conversation only to understand references and follow-up questions.

Previous conversation:
{conversation_text}

Repository context:
{context}

Current user question:
{question}
"""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    return response.text

def embed_text(text: str):

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )

    return response.embeddings[0].values


def embed_texts(texts: list[str]):

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
    )

    return [
        embedding.values
        for embedding in response.embeddings
    ]
