from src.rag.chunker import create_chunks
from src.rag.vector_store import add_documents


def ingest_document(
    filename: str,
    text: str,
):
    """Clean, chunk, and store a document in ChromaDB."""

    chunks = create_chunks(text)

    if not chunks:
        return 0

    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        chunk_id = f"{filename}-{index}"

        ids.append(chunk_id)

        metadatas.append(
            {
                "filename": filename,
                "chunk_index": index,
            }
        )

    add_documents(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return len(chunks)