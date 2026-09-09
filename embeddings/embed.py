from sentence_transformers import SentenceTransformer

# Load the model once — this is important, loading it repeatedly is slow
_model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Takes a list of chunk dicts (with 'content') and adds an 'embedding' field to each.
    """
    texts = [c["content"] for c in chunks]
    vectors = _model.encode(texts, show_progress_bar=True)

    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector.tolist()  # convert numpy array to plain list

    return chunks


if __name__ == "__main__":
    from ingestion.fetch_repo import get_repo_files
    from ingestion.chunker import chunk_text

    files = get_repo_files(owner="pallets", repo="flask", branch="main")
    all_chunks = []
    for f in files:
        all_chunks.extend(chunk_text(f["content"], f["path"]))

    embedded = embed_chunks(all_chunks)

    print(f"Embedded {len(embedded)} chunks.")
    print(f"Vector length: {len(embedded[0]['embedding'])}")
    print(f"Sample vector (first 5 numbers): {embedded[0]['embedding'][:5]}")