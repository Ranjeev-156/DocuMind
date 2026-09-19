import re
from collections import Counter
from math import log, sqrt


def tokenize(text: str) -> list[str]:
    """Convert text into normalized word tokens."""

    return re.findall(
        r"\b[a-zA-Z0-9]+\b",
        text.lower(),
    )


def build_document_vectors(
    documents: list[str],
) -> tuple[list[dict[str, float]], dict[str, float]]:
    """
    Build simple TF-IDF vectors locally.

    No external API is used.
    """

    tokenized_documents = [
        tokenize(document)
        for document in documents
    ]

    document_frequency = Counter()

    for tokens in tokenized_documents:
        for token in set(tokens):
            document_frequency[token] += 1

    total_documents = len(documents)

    idf = {
        token: log(
            (total_documents + 1)
            / (frequency + 1)
        )
        + 1
        for token, frequency in document_frequency.items()
    }

    vectors = []

    for tokens in tokenized_documents:
        counts = Counter(tokens)
        total_tokens = len(tokens)

        vector = {}

        if total_tokens:
            for token, count in counts.items():
                if token in idf:
                    tf = count / total_tokens
                    vector[token] = tf * idf[token]

        vectors.append(vector)

    return vectors, idf


def create_query_vector(
    query: str,
    idf: dict[str, float],
) -> dict[str, float]:
    """Create a TF-IDF vector for a search query."""

    tokens = tokenize(query)
    counts = Counter(tokens)
    total_tokens = len(tokens)

    if not total_tokens:
        return {}

    vector = {}

    for token, count in counts.items():
        if token in idf:
            tf = count / total_tokens
            vector[token] = tf * idf[token]

    return vector


def cosine_similarity(
    vector_a: dict[str, float],
    vector_b: dict[str, float],
) -> float:
    """Calculate cosine similarity between two sparse vectors."""

    if not vector_a or not vector_b:
        return 0.0

    dot_product = sum(
        value * vector_b.get(token, 0.0)
        for token, value in vector_a.items()
    )

    magnitude_a = sqrt(
        sum(value * value for value in vector_a.values())
    )

    magnitude_b = sqrt(
        sum(value * value for value in vector_b.values())
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)