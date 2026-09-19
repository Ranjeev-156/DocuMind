import streamlit as st
from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.6-flash"
REQUEST_TIMEOUT_SECONDS = 30
MAX_OUTPUT_TOKENS = 512
MAX_CONTEXT_CHARS = 10000


@st.cache_resource(show_spinner=False)
def get_client():
    api_key = st.secrets["GEMINI_API_KEY"]
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=REQUEST_TIMEOUT_SECONDS * 1000,
        ),
    )


def generate_answer(question: str, context: str) -> str:
    question = question.strip()
    context = context.strip()

    if not question:
        return "Please enter a question."

    if not context:
        return "I couldn't find relevant information in the provided documents."

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n[Context truncated for speed.]"

    prompt = f"""You are DocuMind AI, a document-only assistant.
Answer ONLY from the document context. Do not use outside knowledge.
If the answer is not present, say: I couldn't find the answer in the provided documents.
Be concise and direct.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}
"""

    try:
        client = get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                thinking_config=types.ThinkingConfig(
                    thinking_level="minimal"
                ),
            ),
        )

        answer = (response.text or "").strip()
        if not answer:
            return "The AI returned an empty answer. Please try again."
        return answer

    except Exception as error:
        message = str(error)
        lower = message.lower()

        if "429" in lower or "resource exhausted" in lower or "quota" in lower:
            raise RuntimeError(
                "Gemini API quota/rate limit was reached. "
                "Check your Google AI Studio quota and API key."
            ) from error

        if "timeout" in lower or "timed out" in lower:
            raise RuntimeError(
                f"Gemini did not respond within {REQUEST_TIMEOUT_SECONDS} seconds. "
                "Please try again."
            ) from error

        raise RuntimeError(f"Gemini generation failed: {message}") from error
