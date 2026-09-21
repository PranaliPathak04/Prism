from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

COLLECTION_NAME = "code_chunks"
_client = QdrantClient(url="http://localhost:6333")

# Simple in-memory cache so we don't rebuild the BM25 index on every call
_bm25_cache = {}


def _tokenize(text: str):
    """Very simple tokenizer: lowercase, split on non-alphanumeric characters."""
    import re
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())


def _load_repo_chunks(repo_name: str):
    """Fetch all chunks for a repo from Qdrant (needed to build the BM25 index)."""
    all_points = []
    offset = None
    while True:
        points, offset = _client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="repo", match=MatchValue(value=repo_name))]
            ),
            limit=200,
            offset=offset,
            with_payload=True,
        )
        all_points.extend(points)
        if offset is None:
            break
    return all_points


def _get_bm25_index(repo_name: str):
    """Builds (or returns cached) BM25 index for a repo."""
    if repo_name in _bm25_cache:
        return _bm25_cache[repo_name]

    points = _load_repo_chunks(repo_name)
    tokenized_corpus = [_tokenize(p.payload["content"]) for p in points]
    bm25 = BM25Okapi(tokenized_corpus)

    _bm25_cache[repo_name] = (bm25, points)
    return bm25, points


def bm25_search(query: str, repo_name: str, top_k: int = 10):
    """Keyword-based search using BM25 over all chunks in a repo."""
    bm25, points = _get_bm25_index(repo_name)
    tokenized_query = _tokenize(query)

    scores = bm25.get_scores(tokenized_query)
    scored = list(zip(points, scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored[:top_k]


if __name__ == "__main__":
    query = "after_request"
    results = bm25_search(query, repo_name="pallets/flask")

    print(f"Query: {query}\n")
    for point, score in results:
        print(f"BM25 score: {score:.4f} | {point.payload['path']} (lines {point.payload['start_line']}-{point.payload['end_line']})")
        print(point.payload["content"][:150])
        print("---")