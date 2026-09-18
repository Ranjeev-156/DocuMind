import chromadb

from src.rag.embeddings import (
    embed_documents,
    embed_query,
)


COLLECTION_NAME = "documind_documents"


def get_client():
    """Create a persistent ChromaDB client."""

    return chromadb.PersistentClient(
        path="./chroma_db"
    )


def get_collection():
    """Get or create the DocuMind collection."""

    client = get_client()

    return client.get_or_create_collection(
        name=COLLECTION_NAME
    )


def add_documents(
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
):
    """Embed and store document chunks in ChromaDB."""

    if not documents:
        return

    if not (
        len(ids)
        == len(documents)
        == len(metadatas)
    ):
        raise ValueError(
            "ids, documents, and metadatas "
            "must have the same length."
        )

    collection = get_collection()

    embeddings = embed_documents(documents)

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )


def search_documents(
    query: str,
    n_results: int = 3,
):
    """Search document chunks using Gemini embeddings."""

    if not query.strip():
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    collection = get_collection()

    if collection.count() == 0:
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    query_embedding = embed_query(query)

    return collection.query(
        query_embeddings=[query_embedding],
        n_results=min(
            n_results,
            collection.count(),
        ),
    )


def get_document_count() -> int:
    """Return the number of stored chunks."""

    collection = get_collection()

    return collection.count()