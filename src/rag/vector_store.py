import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path


DB_PATH = Path("documind.db")


# =========================================================
# SEARCH CONFIGURATION
# =========================================================

STOP_WORDS = {
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
    "did",
    "explain",
    "tell",
    "me",
    "about",
    "give",
    "show",
    "please",
    "write",
    "make",
    "create",
    "notes",
    "note",
    "exam",
    "ready",
    "based",
}


# =========================================================
# DATABASE
# =========================================================

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
# TEXT NORMALIZATION
# =========================================================

def _tokenize(text: str) -> list[str]:
    """
    Convert text into normalized word tokens.
    """

    if not text:
        return []

    return re.findall(
        r"\b[a-zA-Z0-9]+\b",
        str(text).lower(),
    )


def _important_tokens(text: str) -> list[str]:
    """
    Remove common question/instruction words so that
    important subject terms receive more weight.
    """

    tokens = _tokenize(text)

    return [
        token
        for token in tokens
        if token not in STOP_WORDS
    ]


def _normalize_text(text: str) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(text).lower().strip(),
    )


# =========================================================
# PHRASE MATCHING
# =========================================================

def _phrase_score(
    query: str,
    document: str,
) -> float:

    normalized_query = _normalize_text(query)
    normalized_document = _normalize_text(document)

    if not normalized_query:
        return 0.0

    # Exact full query
    if normalized_query in normalized_document:
        return 1.0

    important = _important_tokens(query)

    if not important:
        important = _tokenize(query)

    if not important:
        return 0.0

    # Check consecutive important words
    if len(important) >= 2:

        phrase = " ".join(important)

        if phrase in normalized_document:
            return 0.95

    # Score individual important terms
    matches = 0

    for token in important:

        if re.search(
            rf"\b{re.escape(token)}\b",
            normalized_document,
        ):
            matches += 1

    return matches / len(important)


# =========================================================
# BM25
# =========================================================

def _build_statistics(documents):

    tokenized = [
        _tokenize(document)
        for document in documents
    ]

    document_frequency = Counter()

    for tokens in tokenized:

        for token in set(tokens):
            document_frequency[token] += 1

    total_documents = len(documents)

    average_length = (
        sum(len(tokens) for tokens in tokenized)
        / total_documents
        if total_documents
        else 0
    )

    return (
        tokenized,
        document_frequency,
        average_length,
    )


def _bm25_score(
    query_tokens,
    document_tokens,
    document_frequency,
    total_documents,
    average_length,
):
    """
    Lightweight BM25-style ranking.
    """

    if not query_tokens or not document_tokens:
        return 0.0

    k1 = 1.5
    b = 0.75

    document_length = len(document_tokens)

    frequencies = Counter(document_tokens)

    score = 0.0

    for token in query_tokens:

        if token not in frequencies:
            continue

        df = document_frequency.get(
            token,
            0,
        )

        if df == 0:
            continue

        idf = math.log(
            1
            + (
                total_documents
                - df
                + 0.5
            )
            / (
                df
                + 0.5
            )
        )

        tf = frequencies[token]

        denominator = (
            tf
            + k1
            * (
                1
                - b
                + b
                * (
                    document_length
                    / max(
                        average_length,
                        1,
                    )
                )
            )
        )

        score += (
            idf
            * (
                tf
                * (k1 + 1)
                / denominator
            )
        )

    return score


# =========================================================
# TERM COVERAGE
# =========================================================

def _term_coverage(
    query_tokens,
    document_tokens,
):
    """
    Measures how many important query terms occur
    in the document.
    """

    if not query_tokens:
        return 0.0

    document_set = set(document_tokens)

    matches = sum(
        1
        for token in query_tokens
        if token in document_set
    )

    return matches / len(
        set(query_tokens)
    )


# =========================================================
# EXACT TERM BOOST
# =========================================================

def _exact_term_boost(
    query_tokens,
    document_tokens,
):
    """
    Give additional weight when important subject terms
    occur in the retrieved chunk.
    """

    if not query_tokens:
        return 0.0

    document_set = set(document_tokens)

    matched = (
        set(query_tokens)
        & document_set
    )

    if not matched:
        return 0.0

    boost = 0.0

    for token in matched:

        count = document_tokens.count(token)

        if count >= 5:
            boost += 0.08

        elif count >= 2:
            boost += 0.04

        else:
            boost += 0.02

    return min(
        0.20,
        boost,
    )


# =========================================================
# FINAL SCORE
# =========================================================

def _calculate_score(
    query,
    document,
    filename,
    bm25,
    average_bm25,
):
    """
    Combine multiple local retrieval signals.
    """

    query_tokens = _important_tokens(query)

    if not query_tokens:
        query_tokens = _tokenize(query)

    document_tokens = _tokenize(document)

    coverage = _term_coverage(
        query_tokens,
        document_tokens,
    )

    phrase = _phrase_score(
        query,
        document,
    )

    exact_boost = _exact_term_boost(
        query_tokens,
        document_tokens,
    )

    filename_tokens = set(
        _tokenize(filename)
    )

    filename_matches = (
        set(query_tokens)
        & filename_tokens
    )

    filename_boost = min(
        0.15,
        len(filename_matches) * 0.05,
    )

    normalized_bm25 = 0.0

    if average_bm25 > 0:
        normalized_bm25 = min(
            1.0,
            bm25 / (
                average_bm25 * 2
            ),
        )

    score = (
        normalized_bm25 * 0.45
        + coverage * 0.25
        + phrase * 0.20
        + exact_boost
        + filename_boost
    )

    return min(
        1.0,
        score,
    )


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
    n_results=6,
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

    (
        tokenized_documents,
        document_frequency,
        average_length,
    ) = _build_statistics(
        all_documents
    )

    total_documents = len(rows)

    query_tokens = _important_tokens(query)

    if not query_tokens:
        query_tokens = _tokenize(query)

    scored = []

    raw_bm25_scores = []

    # -----------------------------------------------------
    # Calculate BM25 first
    # -----------------------------------------------------

    for index, row in enumerate(rows):

        score = _bm25_score(
            query_tokens,
            tokenized_documents[index],
            document_frequency,
            total_documents,
            average_length,
        )

        raw_bm25_scores.append(score)

    average_bm25 = (
        sum(raw_bm25_scores)
        / len(raw_bm25_scores)
        if raw_bm25_scores
        else 0.0
    )

    # -----------------------------------------------------
    # Calculate final ranking
    # -----------------------------------------------------

    for index, row in enumerate(rows):

        content = row["content"]

        bm25 = raw_bm25_scores[index]

        score = _calculate_score(
            query=query,
            document=content,
            filename=row["filename"],
            bm25=bm25,
            average_bm25=average_bm25,
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
                "score": score,
                "bm25": bm25,
                "content": content,
                "metadata": metadata,
                "filename": row["filename"],
                "chunk_index": row["chunk_index"],
            }
        )

    # -----------------------------------------------------
    # Sort strongest first
    # -----------------------------------------------------

    scored.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    # -----------------------------------------------------
    # Adaptive relevance selection
    # -----------------------------------------------------

    relevant = []

    for item in scored:

        score = item["score"]

        # Strong results
        if score >= 0.12:
            relevant.append(item)

        # Allow exact important-term matches
        elif (
            _phrase_score(
                query,
                item["content"],
            )
            >= 0.5
        ):
            relevant.append(item)

        if len(relevant) >= n_results:
            break

    # -----------------------------------------------------
    # If nothing passed the filter, return top result
    # when it has at least some lexical evidence.
    # -----------------------------------------------------

    if not relevant and scored:

        best = scored[0]

        best_tokens = set(
            _tokenize(best["content"])
        )

        query_tokens_set = set(
            _important_tokens(query)
        )

        if query_tokens_set & best_tokens:

            relevant = [
                best
            ]

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