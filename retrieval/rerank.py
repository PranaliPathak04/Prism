from sentence_transformers import CrossEncoder

_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(query: str, chunks: list, top_k: int = 5):
    """
    Takes initial retrieval results (Qdrant points) and re-scores them
    using a cross-encoder that reads the query and chunk together.
    Returns chunks sorted by the new, more precise relevance score.
    """
    pairs = [(query, c.payload["content"]) for c in chunks]
    scores = _reranker.predict(pairs)

    scored_chunks = list(zip(chunks, scores))
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    return scored_chunks[:top_k]


if __name__ == "__main__":
    from retrieval.search import search_chunks

    query = "what does the after_request decorator do"
    initial_results = search_chunks(query, repo_name="pallets/flask", top_k=20)  # cast a wider net first

    reranked = rerank(query, initial_results, top_k=5)

    print(f"Query: {query}\n")
    for chunk, score in reranked:
        print(f"Rerank score: {score:.4f} | {chunk.payload['path']} (lines {chunk.payload['start_line']}-{chunk.payload['end_line']})")
        print(chunk.payload["content"][:200])
        print("---")