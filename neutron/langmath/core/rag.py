import hashlib
from datetime import datetime

import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

from neutron.langmath.config import settings

# Initialize ChromaDB Local Client
chroma_client = chromadb.PersistentClient(path=settings.chroma_db_dir)

# Initialize local embedding function
# all-MiniLM-L6-v2 is small, fast, and does well for general text
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Get or create the vector collection
collection = chroma_client.get_or_create_collection(
    name="second_brain", embedding_function=embedding_function
)


def ingest_text(text: str, source: str = "cli"):
    """
    Splits text into chunks, computes embeddings, and stores in ChromaDB.
    """
    # 1. Text Splitting (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_text(text)

    if not chunks:
        return 0

    # Prepare inputs for Chroma
    documents = []
    metadatas = []
    ids = []

    timestamp = datetime.now().isoformat()

    for i, chunk in enumerate(chunks):
        # Create a unique integer ID based on hash of the chunk and timestamp
        chunk_hash = hashlib.md5(chunk.encode("utf-8")).hexdigest()
        chunk_id = f"chunk_{timestamp}_{i}_{chunk_hash[:8]}"

        documents.append(chunk)
        ids.append(chunk_id)
        metadatas.append({"source": source, "timestamp": timestamp, "chunk_index": i})

    # 2. Add to Vector DB (Embeddings are generated automatically by the embedding_function)
    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    return len(chunks)


def get_collection_stats():
    """
    Returns statistics about the current vector collection.
    """
    count = collection.count()
    # Get a sample of the data to show structure
    sample = collection.peek(limit=1)

    # Get unique sources from metadata
    all_data = collection.get(include=["metadatas"])
    sources = set()
    if all_data and all_data["metadatas"]:
        for meta in all_data["metadatas"]:
            if meta and "source" in meta:
                sources.add(meta["source"])

    return {"count": count, "sources": list(sources), "sample": sample}
