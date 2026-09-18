import streamlit as st
from google import genai


MODEL_NAME = "gemini-3.6-flash"


def get_client():
    """Create a Gemini client using the secure API key."""

    api_key = st.secrets["GEMINI_API_KEY"]

    return genai.Client(
        api_key=api_key
    )


def generate_answer(
    question: str,
    context: str,
) -> str:
    """Generate an answer using only the retrieved context."""

    client = get_client()

    prompt = f"""
You are DocuMind AI, an intelligent document assistant.

Answer the user's question using ONLY the information provided
in the document context below.

If the answer cannot be found in the context, say:
"I couldn't find the answer in the provided documents."

Do not invent facts.
Do not use outside knowledge.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
    )

    return interaction.output_text.strip()