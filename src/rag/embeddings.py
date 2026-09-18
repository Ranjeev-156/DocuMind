import streamlit as st

from google import genai
from google.genai import types


MODEL_NAME = "gemini-embedding-001"


def get_client():
    """Create a Gemini client using the secure API key."""

    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Create embeddings for document chunks."""

    if not texts:
        return []

    client = get_client()

    response = client.models.embed_content(
        model=MODEL_NAME,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
        ),
    )

    return [
        embedding.values
        for embedding in response.embeddings
    ]


def embed_query(query: str) -> list[float]:
    """Create an embedding for a user's search query."""

    client = get_client()

    response = client.models.embed_content(
        model=MODEL_NAME,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
        ),
    )

    return response.embeddings[0].values