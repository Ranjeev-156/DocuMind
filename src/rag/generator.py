import json
import re
import socket
import urllib.error
import urllib.request

import streamlit as st


# =========================================================
# CONFIGURATION
# =========================================================

LOCAL_MODEL = "llama3.2:latest"
LOCAL_OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/free"

LOCAL_TIMEOUT_SECONDS = 180
OPENROUTER_TIMEOUT_SECONDS = 45

MAX_OUTPUT_TOKENS = 1024

MAX_CONTEXT_CHARS = 16000
MAX_CONVERSATION_CHARS = 6000


# =========================================================
# PROVIDER NAMES
# =========================================================

PROVIDER_SMART = "Smart Mode"
PROVIDER_LOCAL = "Local AI — Llama 3.2"
PROVIDER_OPENROUTER = "OpenRouter — Free"

PROVIDER_SMART_ALIASES = {
    "Smart Mode",
    "Smart AI",
}


# =========================================================
# ANSWER MODES
# =========================================================

ANSWER_MODE_GROUNDED = "Grounded Mode"
ANSWER_MODE_ADAPTIVE = "Adaptive Mode"

ANSWER_MODE_ALIASES = {
    "Enhanced Mode": ANSWER_MODE_ADAPTIVE,
    "General Mode": ANSWER_MODE_ADAPTIVE,
    "Adaptive Mode": ANSWER_MODE_ADAPTIVE,
    "Grounded Mode": ANSWER_MODE_GROUNDED,
}


# =========================================================
# RETRIEVAL QUERY BUILDER
# =========================================================

def build_retrieval_query(
    question: str,
    conversation_context: str = "",
) -> str:
    """
    Build a focused retrieval query.

    The original question is sent to the generator.
    This function is only responsible for finding the
    most relevant document content.

    Follow-up questions can use recent conversation
    to recover the topic.

    Example:

        User: What is velocity?
        User: Is it a vector quantity?

    Retrieval can understand that "it" refers to velocity.
    """

    question = (question or "").strip()

    if not question:
        return ""

    query = question
    lowered = query.lower()

    # -----------------------------------------------------
    # Follow-up detection
    # -----------------------------------------------------

    follow_up_patterns = [
        r"^\s*(is|are|was|were|does|do|did|can|could)\s+it\b",
        r"^\s*(is|are|was|were|does|do|did|can|could)\s+this\b",
        r"^\s*(is|are|was|were|does|do|did|can|could)\s+that\b",
        r"^\s*what\s+about\b",
        r"^\s*how\s+about\b",
        r"^\s*and\s+what\b",
        r"^\s*and\s+why\b",
        r"^\s*and\s+how\b",
        r"^\s*then\s+why\b",
        r"^\s*why\s+is\s+it\b",
        r"^\s*why\s+does\s+it\b",
        r"^\s*how\s+does\s+it\b",
        r"^\s*how\s+is\s+it\b",
        r"^\s*the\s+above\b",
        r"^\s*this\b",
        r"^\s*that\b",
        r"^\s*these\b",
        r"^\s*those\b",
    ]

    is_follow_up = any(
        re.search(
            pattern,
            lowered,
            flags=re.IGNORECASE,
        )
        for pattern in follow_up_patterns
    )

    # -----------------------------------------------------
    # Remove answer-format instructions
    # -----------------------------------------------------

    patterns = [
        r"\bmake\s+exam[- ]?ready\s+notes?\s+(?:for|on)\s+",
        r"\bgive\s+exam[- ]?ready\s+notes?\s+(?:for|on)\s+",
        r"\bcreate\s+exam[- ]?ready\s+notes?\s+(?:for|on)\s+",

        r"\bmake\s+notes?\s+(?:for|on)\s+",
        r"\bgive\s+notes?\s+(?:for|on)\s+",
        r"\bcreate\s+notes?\s+(?:for|on)\s+",

        r"\btell\s+me\s+about\s+",
        r"\bgive\s+me\s+information\s+(?:about|on)\s+",
        r"\bgive\s+me\s+details\s+(?:about|on)\s+",

        r"\bwhat\s+is\s+",
        r"\bwhat\s+are\s+",
        r"\bwhat\s+was\s+",

        r"\bwho\s+is\s+",
        r"\bwho\s+was\s+",

        r"\bdescribe\s+",
        r"\bdefine\s+",

        r"\bexplain\s+more\s+(?:about|on)\s+",
        r"\bexplain\s+(?:about|on)\s+",
        r"\bexplain\s+",

        r"\bsummarize\s+",
        r"\bsummarise\s+",
    ]

    for pattern in patterns:

        cleaned = re.sub(
            pattern,
            "",
            lowered,
            count=1,
            flags=re.IGNORECASE,
        )

        if cleaned != lowered:

            query = cleaned.strip()
            break

    # -----------------------------------------------------
    # Remove output-format instructions
    # -----------------------------------------------------

    query = re.sub(
        r"\s+in\s+\d+\s+(?:words?|points?|sentences?)\s*$",
        "",
        query,
        flags=re.IGNORECASE,
    )

    query = re.sub(
        r"\s+(?:in|using)\s+\d+\s+(?:points?|bullet points?)\s*$",
        "",
        query,
        flags=re.IGNORECASE,
    )

    query = re.sub(
        r"\s+for\s+(?:a\s+)?\d+\s*[- ]?mark\s+answer\s*$",
        "",
        query,
        flags=re.IGNORECASE,
    )

    query = re.sub(
        r"\s+in\s+detail\s*$",
        "",
        query,
        flags=re.IGNORECASE,
    )

    query = re.sub(
        r"\s+briefly\s*$",
        "",
        query,
        flags=re.IGNORECASE,
    )

    query = re.sub(
        r"\s+clearly\s*$",
        "",
        query,
        flags=re.IGNORECASE,
    )

    query = re.sub(
        r"\s+",
        " ",
        query,
    ).strip()

    # -----------------------------------------------------
    # Add ONLY recent conversation for follow-ups.
    #
    # We deliberately limit this because sending the entire
    # conversation into retrieval makes searches noisier
    # after many questions.
    # -----------------------------------------------------

    if is_follow_up and conversation_context:

        recent_context = _normalize_conversation(
            conversation_context,
            max_chars=2500,
        )

        # Extract previous user messages because they are
        # usually the most useful topic clues.
        previous_user_questions = []

        for line in recent_context.splitlines():

            line = line.strip()

            if line.lower().startswith("user:"):

                previous_question = (
                    line[5:].strip()
                )

                if previous_question:
                    previous_user_questions.append(
                        previous_question
                    )

        if previous_user_questions:

            # Keep the most recent 2 user questions.
            topic_context = " ".join(
                previous_user_questions[-2:]
            )

            query = (
                f"{query} "
                f"{topic_context}"
            )

        else:

            query = (
                f"{query} "
                f"{recent_context}"
            )

    return query if query else question


# =========================================================
# ANSWER MODE
# =========================================================

def _get_answer_mode() -> str:

    mode = st.session_state.get(
        "answer_mode",
        ANSWER_MODE_ADAPTIVE,
    )

    return ANSWER_MODE_ALIASES.get(
        mode,
        ANSWER_MODE_ADAPTIVE,
    )


# =========================================================
# CONVERSATION NORMALIZATION
# =========================================================

def _normalize_conversation(
    conversation_context: str,
    max_chars: int = MAX_CONVERSATION_CHARS,
) -> str:

    if not conversation_context:
        return ""

    conversation_context = str(
        conversation_context
    ).strip()

    if len(conversation_context) <= max_chars:
        return conversation_context

    return conversation_context[
        -max_chars:
    ]


# =========================================================
# ANSWER FORMAT NORMALIZATION
# =========================================================

def _clean_answer_format(answer: str) -> str:
    """
    Clean common formatting artifacts produced by LLMs.

    In particular, convert malformed display-math wrappers
    such as:

        [ \text{Average velocity}=... ]

    into readable Markdown/LaTeX-style output.

    We do NOT rewrite the actual scientific content.
    """

    if not answer:
        return answer

    answer = str(answer).strip()

    # -----------------------------------------------------
    # Remove accidental outer whitespace.
    # -----------------------------------------------------

    answer = answer.replace(
        "\r\n",
        "\n",
    )

    # -----------------------------------------------------
    # Convert common LaTeX commands to readable Markdown
    # where the model has used a simple inline expression.
    # -----------------------------------------------------

    answer = re.sub(
        r"\\text\{([^{}]+)\}",
        r"\1",
        answer,
    )

    answer = re.sub(
        r"\\mathrm\{([^{}]+)\}",
        r"\1",
        answer,
    )

    # -----------------------------------------------------
    # Fix malformed square-bracket math blocks.
    #
    # Example:
    #
    # [ \text{Average velocity} =
    #   \frac{...}{...} ]
    #
    # becomes:
    #
    # $$ ... $$
    #
    # Streamlit's Markdown renderer can then display the
    # equation properly.
    # -----------------------------------------------------

    answer = re.sub(
        r"(?s)\[\s*(\\(?:frac|text|mathrm|sqrt)|[A-Za-z]+)"
        r".*?\s*\]",
        lambda match: (
            "$$"
            + match.group(0)[1:-1].strip()
            + "$$"
        ),
        answer,
    )

    # -----------------------------------------------------
    # Remove accidental triple blank lines.
    # -----------------------------------------------------

    answer = re.sub(
        r"\n{3,}",
        "\n\n",
        answer,
    )

    return answer.strip()


# =========================================================
# PROMPT
# =========================================================

def build_prompt(
    question: str,
    context: str,
    conversation_context: str = "",
    answer_mode: str = ANSWER_MODE_ADAPTIVE,
) -> str:
    """
    Build the main DocuMind AI prompt.

    Grounded Mode:
        Strictly use supported document information.

    Adaptive Mode:
        Use documents as the foundation while allowing
        general knowledge for useful explanation when the
        retrieved information is short.

    Conversation context supports follow-up questions.
    """

    answer_mode = ANSWER_MODE_ALIASES.get(
        answer_mode,
        ANSWER_MODE_ADAPTIVE,
    )

    conversation_context = _normalize_conversation(
        conversation_context
    )

    if answer_mode == ANSWER_MODE_GROUNDED:

        grounding_rules = """
GROUNDING MODE: STRICT

1. Answer using only information supported by the
   retrieved document context and previously grounded
   conversation.

2. Do NOT add outside facts simply because you know them.

3. Do NOT invent missing information.

4. If the documents do not support the requested answer,
   clearly say that the information is not available in
   the provided documents.

5. You may reorganize, summarize, explain or simplify
   information that IS present in the documents.

6. Preserve important definitions, formulas, terminology,
   names, dates, numbers and relationships from the source.

7. Never pretend that outside knowledge came from the
   user's documents.
""".strip()

    else:

        grounding_rules = """
ADAPTIVE MODE

1. Use the retrieved documents as the primary factual
   foundation whenever they are relevant.

2. If the retrieved information is short, incomplete,
   or only a brief definition, do NOT refuse to answer.

3. You may use reliable general knowledge to explain,
   elaborate, simplify, organize or expand the topic.

4. Do not contradict the user's documents.

5. Do not invent document-specific facts.

6. Do not invent names, dates, numbers, quotations,
   formulas or claims and pretend they came from the
   documents.

7. When useful, distinguish between information directly
   supported by the documents and additional explanation.

8. If the documents are unrelated to a normal
   general-knowledge question, answer the question using
   general knowledge.

9. The goal is a useful answer, not merely a repetition
   of the retrieved text.
""".strip()

    conversation_section = (
        conversation_context
        if conversation_context
        else "(No previous conversation.)"
    )

    document_section = (
        context
        if context
        else "(No relevant document context was retrieved.)"
    )

    return f"""
You are DocuMind AI, an intelligent learning and
document-analysis assistant.

Give accurate, clear and useful answers.

The user may ask for:

- definitions
- explanations
- why/how questions
- comparisons
- examples
- calculations
- summaries
- notes
- exam-ready notes
- revision notes
- exact point counts
- approximate word counts
- mark-based answers
- follow-up questions
- conceptual questions
- practical questions

==================================================
ANSWER MODE
==================================================

{answer_mode}

==================================================
GROUNDING RULES
==================================================

{grounding_rules}

==================================================
CONVERSATION CONTEXT
==================================================

Use previous conversation when needed to understand:

- it
- they
- this
- that
- these
- those
- the above
- the previous answer
- the previous point
- what about it
- why is it
- how does it work

Do not unnecessarily repeat old answers.

{conversation_section}

==================================================
USER REQUEST
==================================================

{question}

==================================================
RETRIEVED DOCUMENT CONTEXT
==================================================

{document_section}

==================================================
ANSWER FORMAT
==================================================

Follow explicit formatting instructions.

Examples:

"Explain velocity"
→ Give a clear explanation.

"Elaborate velocity in 200 words"
→ Give approximately 200 words.

"Make notes for velocity in 5 points"
→ Give exactly 5 useful points.

"Make exam-ready notes for velocity"
→ Use clear headings and revision-friendly structure.

"Give a 2-mark answer"
→ Give an appropriately concise exam answer.

"Compare velocity and speed"
→ Clearly compare the requested concepts.

Do not unnecessarily mention these instructions.

==================================================
MATHEMATICAL FORMATTING
==================================================

When giving equations:

1. Use simple readable notation when possible.

2. For display equations, use standard LaTeX:
   $$ equation $$

3. Do not wrap equations in square brackets like:
   [ equation ]

4. Do not use unnecessary LaTeX commands.

5. For simple school-level formulas, readable text is
   preferred when it improves clarity.

Example:

Average velocity = displacement / time

For equations, prefer readable notation such as:

v = change in position / change in time
 
==================================================
FINAL RULE
==================================================

Answer directly.

Be accurate, clear and useful.

Do not simply copy retrieved documents when the user
asks for explanation or elaboration.

If the user requests a specific number of points,
follow that number.

If the user requests an approximate word count,
target it.

If the user asks a follow-up question, resolve the
reference using conversation context before answering.
""".strip()


# =========================================================
# OPENROUTER CONTENT EXTRACTION
# =========================================================

def _extract_openrouter_content(result) -> str:

    if not isinstance(result, dict):
        return ""

    choices = result.get("choices") or []

    if not choices:
        return ""

    first_choice = choices[0] or {}

    if not isinstance(first_choice, dict):
        return ""

    message = first_choice.get("message") or {}

    if not isinstance(message, dict):
        return ""

    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):

        parts = []

        for item in content:

            if not isinstance(item, dict):
                continue

            text = item.get("text")

            if text:
                parts.append(
                    str(text)
                )

        return "\n".join(parts).strip()

    if content is None:
        return ""

    return str(content).strip()


# =========================================================
# LOCAL OLLAMA
# =========================================================

def _generate_local(
    question: str,
    context: str,
    conversation_context: str = "",
    answer_mode: str = ANSWER_MODE_ADAPTIVE,
) -> str:
    """
    Generate an answer using local Ollama/Llama 3.2.

    Uses the same HTTP approach tested successfully
    outside Streamlit.
    """

    prompt = build_prompt(
        question=question,
        context=context,
        conversation_context=conversation_context,
        answer_mode=answer_mode,
    )

    payload = {
        "model": LOCAL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": MAX_OUTPUT_TOKENS,
            "keep_alive": "5m",
        },
    }

    try:
        import requests

        response = requests.post(
            LOCAL_OLLAMA_URL,
            json=payload,
            timeout=(5, LOCAL_TIMEOUT_SECONDS),
        )

        response.raise_for_status()

        result = response.json()

        answer = (
            result
            .get("message", {})
            .get("content", "")
        )

        if not isinstance(answer, str):
            answer = str(answer or "")

        answer = answer.strip()

        if not answer:
            raise RuntimeError(
                "Llama 3.2 returned an empty answer."
            )

        return _clean_answer_format(answer)

    except requests.exceptions.ConnectTimeout as error:
        raise RuntimeError(
            "Could not connect to Ollama within 5 seconds."
        ) from error

    except requests.exceptions.ReadTimeout as error:
        raise RuntimeError(
            "Llama 3.2 took too long to generate the answer."
        ) from error

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Could not connect to Ollama. "
            "Make sure Ollama is running."
        ) from error

    except requests.exceptions.HTTPError as error:
        try:
            details = response.text[:500]
        except Exception:
            details = str(error)

        raise RuntimeError(
            f"Ollama returned an HTTP error: {details}"
        ) from error

    except ValueError as error:
        raise RuntimeError(
            "Ollama returned an invalid JSON response."
        ) from error

    except RuntimeError:
        raise

    except Exception as error:
        raise RuntimeError(
            f"Local AI generation failed: {error}"
        ) from error
# =========================================================
# OPENROUTER API KEY
# =========================================================

def get_openrouter_key() -> str:
    """Read the OpenRouter API key from Streamlit Secrets."""

    try:
        api_key = st.secrets["OPENROUTER_API_KEY"]
    except Exception as error:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing from Streamlit Secrets."
        ) from error

    if not api_key or not str(api_key).strip():
        raise RuntimeError(
            "OPENROUTER_API_KEY is empty."
        )

    return str(api_key).strip()
# =========================================================
# OPENROUTER
# =========================================================

def _generate_openrouter(
    question: str,
    context: str,
    conversation_context: str = "",
    answer_mode: str = ANSWER_MODE_ADAPTIVE,
) -> str:

    api_key = get_openrouter_key()

    prompt = build_prompt(
        question=question,
        context=context,
        conversation_context=conversation_context,
        answer_mode=answer_mode,
    )

    payload = {
        "model": OPENROUTER_MODEL,

        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],

        "max_tokens": MAX_OUTPUT_TOKENS,

        "temperature": 0.2,
    }

    data = json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")

    request = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://documind.streamlit.app",
            "X-Title": "DocuMind AI",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=OPENROUTER_TIMEOUT_SECONDS,
        ) as response:

            raw_response = (
                response
                .read()
                .decode("utf-8")
            )

            result = json.loads(
                raw_response
            )

        answer = _extract_openrouter_content(
            result
        )

        if not answer:

            raise RuntimeError(
                "OpenRouter returned an empty answer."
            )

        return _clean_answer_format(
            answer
        )

    except urllib.error.HTTPError as error:

        try:

            error_body = (
                error
                .read()
                .decode("utf-8")
            )

            error_data = json.loads(
                error_body
            )

            error_object = (
                error_data.get(
                    "error",
                    {},
                )
                or {}
            )

            error_message = (
                error_object.get(
                    "message",
                    error_body,
                )
            )

        except Exception:

            error_message = str(error)

        if error.code == 429:

            raise RuntimeError(
                "OpenRouter free-model rate or "
                "daily limit was reached. "
                "Please try again later."
            ) from error

        if error.code in (401, 403):

            raise RuntimeError(
                "OpenRouter API key was rejected. "
                "Check OPENROUTER_API_KEY in "
                "Streamlit Secrets."
            ) from error

        raise RuntimeError(
            f"OpenRouter API error "
            f"({error.code}): {error_message}"
        ) from error

    except urllib.error.URLError as error:

        raise RuntimeError(
            "Could not connect to OpenRouter. "
            "Please check your internet connection."
        ) from error

    except socket.timeout as error:

        raise RuntimeError(
            "OpenRouter did not respond within "
            f"{OPENROUTER_TIMEOUT_SECONDS} seconds."
        ) from error

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "OpenRouter returned an invalid response."
        ) from error

    except RuntimeError:
        raise

    except Exception as error:

        raise RuntimeError(
            f"OpenRouter generation failed: {error}"
        ) from error


# =========================================================
# MAIN GENERATION FUNCTION
# =========================================================

def generate_answer(
    question: str,
    context: str = "",
    conversation_context: str = "",
    answer_mode: str | None = None,
) -> str:
    """
    Generate an answer using the selected provider.

    Backwards compatible:

        generate_answer(question, context)

    New usage:

        generate_answer(
            question,
            context,
            conversation_context,
            answer_mode,
        )
    """

    question = (question or "").strip()
    context = (context or "").strip()

    if not question:
        return "Please enter a question."


    # =====================================================
    # ANSWER MODE
    # =====================================================

    if answer_mode is None:

        answer_mode = _get_answer_mode()

    else:

        answer_mode = ANSWER_MODE_ALIASES.get(
            answer_mode,
            ANSWER_MODE_ADAPTIVE,
        )


    # =====================================================
    # GROUNDING CHECK
    # =====================================================

    if (
        answer_mode == ANSWER_MODE_GROUNDED
        and not context
    ):

        return (
            "I couldn't find enough supporting information "
            "in the provided documents to answer this "
            "question in Grounded Mode."
        )


    # =====================================================
    # CONTEXT LIMIT
    # =====================================================

    if len(context) > MAX_CONTEXT_CHARS:

        context = (
            context[:MAX_CONTEXT_CHARS]
            + "\n\n"
            "[Additional retrieved context "
            "was truncated for speed.]"
        )


    conversation_context = _normalize_conversation(
        conversation_context
    )


    # =====================================================
    # PROVIDER
    # =====================================================

    provider = st.session_state.get(
        "ai_provider",
        PROVIDER_SMART,
    )

    if provider in PROVIDER_SMART_ALIASES:

        provider = PROVIDER_SMART


    # =====================================================
    # LOCAL AI
    # =====================================================

    if provider == PROVIDER_LOCAL:

        return _generate_local(
            question=question,
            context=context,
            conversation_context=conversation_context,
            answer_mode=answer_mode,
        )


    # =====================================================
    # OPENROUTER
    # =====================================================

    if provider == PROVIDER_OPENROUTER:

        return _generate_openrouter(
            question=question,
            context=context,
            conversation_context=conversation_context,
            answer_mode=answer_mode,
        )


    # =====================================================
    # SMART AI
    #
    # OpenRouter FIRST
    # Local Llama 3.2 SECOND
    # =====================================================

    if provider == PROVIDER_SMART:

        openrouter_error = None

        try:

            return _generate_openrouter(
                question=question,
                context=context,
                conversation_context=conversation_context,
                answer_mode=answer_mode,
            )

        except Exception as error:

            openrouter_error = error


        # -------------------------------------------------
        # Fast local fallback
        # -------------------------------------------------

        try:

            return _generate_local(
                question=question,
                context=context,
                conversation_context=conversation_context,
                answer_mode=answer_mode,
            )

        except Exception as local_error:

            raise RuntimeError(
                "Smart AI could not generate an answer.\n\n"
                f"OpenRouter: {openrouter_error}\n"
                f"Local Llama 3.2: {local_error}"
            ) from local_error


    # =====================================================
    # UNKNOWN PROVIDER
    # =====================================================

    raise RuntimeError(
        f"Unknown AI provider: {provider}"
    )