from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

COLLECTION_NAME = "code_chunks"
VECTOR_SIZE = 384  # must match our embedding model's output size

_client = QdrantClient(url="http://localhost:6333")


def ensure_collection(force_recreate: bool = False):
    """Create the collection if it doesn't already exist.If force_recreate is True, delete and recreate it.(avoids duplicates when re-running the script)"""
    existing = [c.name for c in _client.get_collections().collections]

    if force_recreate and COLLECTION_NAME in existing:
        _client.delete_collection(collection_name=COLLECTION_NAME)
        existing.remove(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'(force_recreate=True)")

    if COLLECTION_NAME not in existing:
        _client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"Created collection '{COLLECTION_NAME}'")
    else:
        print(f"Collection '{COLLECTION_NAME}' already exists")


def store_chunks(chunks: list[dict], repo_name: str):
    """
    Upload embedded chunks into Qdrant.
    Each chunk dict must already have an 'embedding' field.
    """
    points = []
    for chunk in chunks:
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),  # unique ID per chunk
                vector=chunk["embedding"],
                payload={
                    "repo": repo_name,
                    "path": chunk["path"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "content": chunk["content"],
                },
            )
        )

    _client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Stored {len(points)} chunks in Qdrant.")

def index_repo(owner:str, repo:str, branch:str="main"):
    """
    Fetches a GitHub repo, chunks its files, embeds them, and stores them in Qdrant.
    Full pipeline: fetch -> chunk -> embed -> store vectors -> extract & store call graph.
    Returns a summary dict.
    """
    from ingestion.fetch_repo import get_repo_files
    from ingestion.ast_chunker import chunk_file
    from embeddings.embed import embed_chunks
    from graph.graph_store import init_db, clear_repo_edges, store_edges
    from graph.call_extractor import extract_calls

    repo_name = f"{owner}/{repo}"

    

    files = get_repo_files(owner=owner, repo=repo, branch=branch)
    all_chunks = []
    all_edges = []
    for f in files:
        all_chunks.extend(chunk_file(f["content"], f["path"]))
        if f["path"].endswith(".py"):
            all_edges.extend(extract_calls(f["content"], f["path"]))


    embedded = embed_chunks(all_chunks)
    ensure_collection(force_recreate=False)  # dont wipe other repos in the same Qdrant instance
    store_chunks(embedded, repo_name=repo_name)

    init_db()
    clear_repo_edges(repo_name)
    store_edges(all_edges, repo_name=repo_name)

    return {
        "repo" : repo_name,
        "files_processed" : len(files),
        "chunks_stored" : len(embedded),
        "call_edges_stored" : len(all_edges),
    }

if __name__ == "__main__":
    results = index_repo("pallets", "flask", branch="main")
    print(results)

    