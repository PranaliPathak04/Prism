from retrieval.search import search_chunks
from retrieval.bm25_search import bm25_search
from retrieval.rerank import rerank


def reciprocal_rank_fusion(vector_results, bm25_results, k: int = 60):
    """
    Combines two ranked lists using Reciprocal Rank Fusion (RRF).
    Each result's score is 1 / (k + rank). Chunks appearing in both
    lists accumulate scores from both, boosting genuinely strong matches.
    """
    scores = {}
    chunk_lookup = {}

    for rank, point in enumerate(vector_results):
        key = point.id
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        chunk_lookup[key] = point

    for rank, (point, _) in enumerate(bm25_results):
        key = point.id
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        chunk_lookup[key] = point

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [chunk_lookup[key] for key, score in fused]


def hybrid_search(query: str, repo_name: str, fused_top_k: int = 20, final_top_k: int = 5):
    vector_results = search_chunks(query, repo_name, top_k=fused_top_k)
    bm25_results = bm25_search(query, repo_name, top_k=fused_top_k)

    fused = reciprocal_rank_fusion(vector_results, bm25_results)[:fused_top_k]
    reranked = rerank(query, fused , top_k=final_top_k)
    return reranked


if __name__ == "__main__":
    query = "what does the after_request decorator do"
    results = hybrid_search(query, repo_name="pallets/flask")

    print(f"Query: {query}\n")
    for chunk, score in results:
        print(f"Fused score: {score:.4f} | {chunk.payload['path']} (lines {chunk.payload['start_line']}-{chunk.payload['end_line']})")
        print(chunk.payload["content"][:150])
        print("---")