from qdrant_client import QdrantClient

import uuid
import hashlib
from qdrant_client.models import Distance ,Filter, FieldCondition, MatchValue , VectorParams, PointStruct

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

    


def make_chunk_id(repo_name: str, chunk: dict) -> str:
    """
    Deterministic ID :same repo + path + line range -> same ID, so we don't store duplicates.
    Re indxing unchanged files will overwrite the same points in Qdrant instead of creating duplicates.
    """
    raw = f"{repo_name}:{chunk['path']}:{chunk['start_line']}:{chunk['content']}"
    hash_hex = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return str(uuid.UUID(hash_hex[:32]))  # use first 32 hex chars to make a UUID


def store_chunks(chunks: list[dict], repo_name: str):
    """
    Upload embedded chunks into Qdrant.
    Each chunk dict must already have an 'embedding' field.
    """
    points = []
    for chunk in chunks:
        points.append(
            PointStruct(
                id=make_chunk_id(repo_name, chunk),  # unique ID per chunk
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

def clear_repo_chunks(repo_name: str):
    """
    Delete all chunks in Qdrant for a given repo.
    Useful if you want to re-index a repo from scratch.
    """
    _client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[FieldCondition(key="repo", match=MatchValue(value=repo_name))]
        )
    )
    print(f"Deleted all chunks for repo '{repo_name}' from Qdrant.")

def clear_repo_file_chunks(repo_name: str, path: str):
    """Deletes chunks for one specific file within a repo (used for changed/deleted files)."""
    _client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(key="repo", match=MatchValue(value=repo_name)),
                FieldCondition(key="path", match=MatchValue(value=path)),
            ]
        ),
    )

def index_repo(owner:str, repo:str, branch:str="main"):
    """
    Fetches a GitHub repo, chunks its files, embeds them, and stores them in Qdrant.
    Full pipeline: fetch -> chunk -> embed -> store vectors -> extract & store call graph.
    Returns a summary dict.
    """
    from ingestion.fetch_repo import get_repo_files
    from ingestion.ast_chunker import chunk_file
    from embeddings.embed import embed_chunks
    from graph.graph_store import (
        init_db, store_edges,
        init_file_hashes_table, get_stored_file_hashes, update_file_hashes,hash_content,
        clear_file_edges, remove_file_hashes
    )
    from graph.call_extractor import extract_calls

    repo_name = f"{owner}/{repo}"

    init_file_hashes_table()
    init_db() # initialize the SQLite database for storing call graph edges
    old_hashes = get_stored_file_hashes(repo_name) #what files have we already processed and stored hashes for

    
    files = get_repo_files(owner=owner, repo=repo, branch=branch)

    new_hashes = {}
    changed_files = []
    unchanged_count = 0

    for f in files:
        content_hash = hash_content(f["content"])
        new_hashes[f["path"]] = content_hash

        if old_hashes.get(f["path"]) == content_hash:
            unchanged_count += 1
            continue  # skip unchanged files

        changed_files.append(f)
    print(f"Found {len(changed_files)} changed/new files, {unchanged_count} unchanged files skipped.")

    all_chunks = []
    all_edges = []
    for f in changed_files:
        all_chunks.extend(chunk_file(f["content"], f["path"]))
        if f["path"].endswith(".py"):
            all_edges.extend(extract_calls(f["content"], f["path"]))


    embedded = embed_chunks(all_chunks) if all_chunks else []

    ensure_collection(force_recreate=False)

    #remove chunks for files that were deleted from repo
    deleted_paths = set(old_hashes.keys()) - set(new_hashes.keys())

    for path in deleted_paths:
        clear_repo_file_chunks(repo_name,path)  # remove old chunks for this repo
        clear_file_edges(repo_name,path)  # remove edges for this file

    #remove old chunks for changed files and store new ones
    for f in changed_files:
        clear_repo_file_chunks(repo_name, f["path"])  # remove old chunks for this repo
        clear_file_edges(repo_name, f["path"])  # remove edges for this file

    if embedded:
        store_chunks(embedded, repo_name=repo_name)

    
   
    store_edges(all_edges, repo_name=repo_name)

    update_file_hashes(repo_name,list(new_hashes.items()))  # update stored hashes for all files in repo
    remove_file_hashes(repo_name,deleted_paths)  # remove hashes for deleted files


    return {
        "repo" : repo_name,
        "files_total" : len(files),
        "files_changed" : len(changed_files),
        "files_unchanged" : unchanged_count,
        "files_deleted" : len(deleted_paths),

        "chunks_stored" : len(embedded),
        "call_edges_stored" : len(all_edges),
    }

if __name__ == "__main__":
    results = index_repo("pallets", "flask", branch="main")
    print(results)

    