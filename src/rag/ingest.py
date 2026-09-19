from src.rag.chunker import create_chunks
from src.rag.vector_store import add_documents


def ingest_document(
    workspace_id,
    filename,
    text,
):

    chunks = create_chunks(text)

    if not chunks:
        return 0

    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks):

        ids.append(
            f"{filename}-{index}"
        )

        metadatas.append(
            {
                "filename": filename,
                "chunk_index": index,
            }
        )

    add_documents(
        workspace_id=workspace_id,
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return len(chunks)