from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from embeddings.embed import _model  # reuse the same loaded model

COLLECTION_NAME = "code_chunks"
_client = QdrantClient(url="http://localhost:6333")


def search_chunks(query: str, repo_name: str, top_k: int = 5):
    """
    Embed the query and search Qdrant for the most similar chunks,
    filtered to a specific repo.
    """
    query_vector = _model.encode(query).tolist()

    results =_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="repo", match=MatchValue(value=repo_name))]
        ),
        limit=top_k,
    )

    return results.points  # list of PointStruct with score and payload


if __name__ == "__main__":
    query = "how is the flask app created"
    results = search_chunks(query, repo_name="pallets/flask")

    print(f"Query: {query}\n")
    for r in results:
        print(f"Score: {r.score:.4f} | {r.payload['path']} (lines {r.payload['start_line']}-{r.payload['end_line']})")
        print(r.payload["content"][:150])
        print("---")