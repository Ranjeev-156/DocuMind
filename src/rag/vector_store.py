import json
from streamlit_js_eval import streamlit_js_eval
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path


REMEMBER_WORKSPACE_KEY = "documind_remembered_workspace"


# =========================================================
# BROWSER WORKSPACE MEMORY
# =========================================================

def get_remembered_workspace():
    """Read the remembered workspace ID from this browser."""
    try:
        value = streamlit_js_eval(
            js_expressions=f"""
                localStorage.getItem("{REMEMBER_WORKSPACE_KEY}")
            """,
            want_output=True,
            key="read_remembered_workspace",
        )

        if value and str(value).strip():
            return str(value).strip()

    except Exception:
        pass

    return None


def remember_workspace(workspace_id):
    """Save only the workspace ID in this browser."""
    if not workspace_id:
        return

    safe_id = (
        str(workspace_id)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
    )

    try:
        streamlit_js_eval(
            js_expressions=f"""
                localStorage.setItem(
                    "{REMEMBER_WORKSPACE_KEY}",
                    "{safe_id}"
                );
            """,
            want_output=False,
            key="save_remembered_workspace",
        )
    except Exception:
        pass


def forget_workspace():
    """Remove the remembered workspace from this browser."""
    try:
        streamlit_js_eval(
            js_expressions=f"""
                localStorage.removeItem("{REMEMBER_WORKSPACE_KEY}");
            """,
            want_output=False,
            key="remove_remembered_workspace",
        )
    except Exception:
        pass


# =========================================================
# DATABASE
# =========================================================

DB_PATH = Path("documind.db")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():

    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_documents_workspace
        ON documents(workspace_id)
        """
    )

    connection.commit()
    connection.close()


initialize_database()


# =========================================================
# TEXT PROCESSING
# =========================================================

def _tokenize(text: str):
    """
    Convert text into lowercase word tokens.

    Example:
        "What is Motion?"
        -> ["what", "is", "motion"]
    """
    return re.findall(
        r"\b[a-zA-Z0-9_]+\b",
        text.lower(),
    )


def _normalize_text(text: str):
    """Normalize text for phrase/substring matching."""
    return re.sub(
        r"\s+",
        " ",
        str(text).lower().strip(),
    )


def _calculate_idf(documents):

    total_documents = len(documents)

    if total_documents == 0:
        return {}

    document_frequency = Counter()

    for document in documents:

        tokens = set(_tokenize(document))

        for token in tokens:
            document_frequency[token] += 1

    idf = {}

    for token, frequency in document_frequency.items():

        idf[token] = (
            math.log(
                (1 + total_documents)
                / (1 + frequency)
            )
            + 1
        )

    return idf


def _create_vector(text, idf):

    tokens = _tokenize(text)
    counts = Counter(tokens)

    vector = {}

    for token, count in counts.items():

        if token in idf:

            vector[token] = (
                count * idf[token]
            )

    return vector


def _cosine_similarity(vector_a, vector_b):

    if not vector_a or not vector_b:
        return 0.0

    common = (
        set(vector_a)
        & set(vector_b)
    )

    dot_product = sum(
        vector_a[token]
        * vector_b[token]
        for token in common
    )

    magnitude_a = math.sqrt(
        sum(
            value ** 2
            for value in vector_a.values()
        )
    )

    magnitude_b = math.sqrt(
        sum(
            value ** 2
            for value in vector_b.values()
        )
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (
        magnitude_a * magnitude_b
    )


# =========================================================
# HYBRID RETRIEVAL
# =========================================================

def _calculate_lexical_score(query, document):
    """
    Calculate how strongly the document matches
    the actual words in the user's question.
    """

    query_tokens = _tokenize(query)

    if not query_tokens:
        return 0.0

    document_tokens = set(
        _tokenize(document)
    )

    matched_tokens = [
        token
        for token in query_tokens
        if token in document_tokens
    ]

    if not matched_tokens:
        return 0.0

    # Remove duplicate query words.
    unique_query_tokens = set(query_tokens)
    unique_matched_tokens = set(matched_tokens)

    coverage = (
        len(unique_matched_tokens)
        / len(unique_query_tokens)
    )

    # Stronger boost when the important query word
    # appears multiple times in the document.
    document_counter = Counter(
        _tokenize(document)
    )

    frequency_bonus = 0.0

    for token in unique_matched_tokens:
        frequency = document_counter[token]

        if frequency >= 5:
            frequency_bonus += 0.10
        elif frequency >= 2:
            frequency_bonus += 0.05

    return min(
        1.0,
        coverage + frequency_bonus,
    )


def _calculate_phrase_score(query, document):
    """
    Detect exact multi-word phrases and single-word
    phrase presence.
    """

    normalized_query = _normalize_text(query)
    normalized_document = _normalize_text(document)

    if not normalized_query:
        return 0.0

    # Exact complete query.
    if normalized_query in normalized_document:
        return 1.0

    query_tokens = _tokenize(query)

    if not query_tokens:
        return 0.0

    # For short questions such as:
    # "what is motion"
    #
    # the meaningful content word "motion" should still
    # receive a useful score.
    meaningful_tokens = [
        token
        for token in query_tokens
        if token not in {
            "what",
            "is",
            "are",
            "was",
            "were",
            "the",
            "a",
            "an",
            "of",
            "to",
            "in",
            "on",
            "for",
            "and",
            "or",
            "how",
            "why",
            "when",
            "where",
            "who",
            "which",
            "can",
            "could",
            "does",
            "do",
        }
    ]

    if not meaningful_tokens:
        meaningful_tokens = query_tokens

    matches = sum(
        1
        for token in meaningful_tokens
        if token in normalized_document
    )

    return matches / len(meaningful_tokens)


def _calculate_hybrid_score(
    query,
    document,
    cosine_score,
):
    """
    Combine semantic-ish TF-IDF similarity with
    exact lexical and phrase matching.

    This is intentionally lightweight and runs locally.
    """

    lexical_score = _calculate_lexical_score(
        query,
        document,
    )

    phrase_score = _calculate_phrase_score(
        query,
        document,
    )

    # Main score.
    #
    # Cosine handles general word similarity.
    # Lexical matching protects exact terms.
    # Phrase matching makes short questions much stronger.
    score = (
        (cosine_score * 0.50)
        + (lexical_score * 0.30)
        + (phrase_score * 0.20)
    )

    # Strong protection for exact meaningful terms.
    query_tokens = set(_tokenize(query))
    document_tokens = set(_tokenize(document))

    stop_words = {
        "what",
        "is",
        "are",
        "was",
        "were",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "how",
        "why",
        "when",
        "where",
        "who",
        "which",
        "can",
        "could",
        "does",
        "do",
    }

    important_query_tokens = (
        query_tokens - stop_words
    )

    exact_important_matches = (
        important_query_tokens
        & document_tokens
    )

    if exact_important_matches:
        score += 0.15

    return min(1.0, score)


# =========================================================
# ADD DOCUMENTS
# =========================================================

def add_documents(
    workspace_id,
    ids,
    documents,
    metadatas,
):

    if not documents:
        return

    if not (
        len(ids)
        == len(documents)
        == len(metadatas)
    ):
        raise ValueError(
            "ids, documents and metadatas "
            "must have the same length."
        )

    connection = get_connection()

    for index, document in enumerate(documents):

        metadata = metadatas[index] or {}

        filename = metadata.get(
            "filename",
            "Unknown",
        )

        chunk_index = metadata.get(
            "chunk_index",
            index,
        )

        connection.execute(
            """
            INSERT OR REPLACE INTO documents
            (
                id,
                workspace_id,
                filename,
                chunk_index,
                content,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"{workspace_id}:{ids[index]}",
                workspace_id,
                filename,
                chunk_index,
                document,
                json.dumps(metadata),
            ),
        )

    connection.commit()
    connection.close()


# =========================================================
# SEARCH
# =========================================================

def search_documents(
    workspace_id,
    query,
    n_results=3,
):

    if not query or not query.strip():

        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            filename,
            chunk_index,
            content,
            metadata
        FROM documents
        WHERE workspace_id = ?
        """,
        (workspace_id,),
    ).fetchall()

    connection.close()

    if not rows:

        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    all_documents = [
        row["content"]
        for row in rows
    ]

    idf = _calculate_idf(
        all_documents
    )

    query_vector = _create_vector(
        query,
        idf,
    )

    scored = []

    for row in rows:

        content = row["content"]

        document_vector = _create_vector(
            content,
            idf,
        )

        cosine_score = _cosine_similarity(
            query_vector,
            document_vector,
        )

        lexical_score = _calculate_lexical_score(
            query,
            content,
        )

        phrase_score = _calculate_phrase_score(
            query,
            content,
        )

        hybrid_score = _calculate_hybrid_score(
            query,
            content,
            cosine_score,
        )

        metadata = {}

        if row["metadata"]:

            try:
                metadata = json.loads(
                    row["metadata"]
                )

            except Exception:
                metadata = {}

        scored.append(
            {
                "score": hybrid_score,
                "cosine": cosine_score,
                "lexical": lexical_score,
                "phrase": phrase_score,
                "content": content,
                "metadata": metadata,
            }
        )

    # Highest hybrid score first.
    scored.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    # -----------------------------------------------------
    # RELEVANCE FILTER
    # -----------------------------------------------------
    #
    # Do NOT simply require cosine > 0.
    #
    # A document can be highly relevant because an exact
    # word appears even when the TF-IDF cosine score is weak.
    #
    relevant = [
        item
        for item in scored
        if (
            item["score"] >= 0.08
            and (
                item["cosine"] > 0
                or item["lexical"] > 0
                or item["phrase"] > 0
            )
        )
    ][:n_results]

    return {
        "documents": [
            [
                item["content"]
                for item in relevant
            ]
        ],
        "metadatas": [
            [
                item["metadata"]
                for item in relevant
            ]
        ],
        "distances": [
            [
                max(
                    0.0,
                    1.0 - item["score"],
                )
                for item in relevant
            ]
        ],
    }


# =========================================================
# DOCUMENT COUNT
# =========================================================

def get_document_count(workspace_id):

    connection = get_connection()

    result = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM documents
        WHERE workspace_id = ?
        """,
        (workspace_id,),
    ).fetchone()

    connection.close()

    return result["count"]


# =========================================================
# DOCUMENT LIST
# =========================================================

def list_documents(workspace_id):

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            filename,
            COUNT(*) AS chunks
        FROM documents
        WHERE workspace_id = ?
        GROUP BY filename
        ORDER BY filename
        """,
        (workspace_id,),
    ).fetchall()

    connection.close()

    return [
        {
            "filename": row["filename"],
            "chunks": row["chunks"],
        }
        for row in rows
    ]


# =========================================================
# DELETE DOCUMENT
# =========================================================

def delete_document(
    workspace_id,
    filename,
):

    connection = get_connection()

    cursor = connection.execute(
        """
        DELETE FROM documents
        WHERE workspace_id = ?
        AND filename = ?
        """,
        (
            workspace_id,
            filename,
        ),
    )

    deleted = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted