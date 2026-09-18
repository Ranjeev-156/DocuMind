import chromadb


COLLECTION_NAME = "documind_documents"


def get_client():
    """Create a ChromaDB client."""
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
    """Add document chunks to ChromaDB."""
    collection = get_collection()

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )


def search_documents(
    query: str,
    n_results: int = 3,
):
    """Search stored document chunks."""
    collection = get_collection()

    return collection.query(
        query_texts=[query],
        n_results=n_results,
    )


def get_document_count() -> int:
    """Return the number of stored chunks."""
    collection = get_collection()

    return collection.count()