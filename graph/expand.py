from graph.graph_store import get_callees, get_callers
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

COLLECTION_NAME = "code_chunks"
_client = QdrantClient(url="http://localhost:6333")


def get_function_name_from_chunk(chunk) -> str | None:
    """
    Best-effort: extract the function name a chunk represents, by
    parsing the 'def X(' pattern out of its content.
    """
    import re
    match = re.search(r"def (\w+)\s*\(", chunk.payload["content"])
    return match.group(1) if match else None


def fetch_chunk_for_function(function_name: str, repo_name: str, path_hint: str = None):
    """
    Finds a stored chunk whose content defines this function name.
    path_hint narrows the search to a specific file if provided (helps disambiguate).
    """
    must = [
        FieldCondition(key="repo", match=MatchValue(value=repo_name)),
    ]
    if path_hint:
        must.append(FieldCondition(key="path", match=MatchValue(value=path_hint)))

    points, _ = _client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(must=must),
        limit=500,
    )

    import re
    pattern = re.compile(rf"def {re.escape(function_name)}\s*\(")
    for p in points:
        if pattern.search(p.payload["content"]):
            return p
    return None


def expand_with_graph(chunks: list, repo_name: str, max_extra: int = 5):
    """
    Given retrieved chunks, find what functions they call (1 hop),
    and fetch those chunks too, if not already present.
    """
    seen_paths_lines = {(c.payload["path"], c.payload["start_line"]) for c in chunks}
    extra_chunks = []

    for chunk in chunks:
        fn_name = get_function_name_from_chunk(chunk)
        if not fn_name:
            continue

        callees = get_callees(fn_name, repo_name)
        for callee_name, callee_path in callees:
            related_chunk = fetch_chunk_for_function(callee_name, repo_name, path_hint=callee_path)
            if related_chunk is None:
                continue
            key = (related_chunk.payload["path"], related_chunk.payload["start_line"])
            if key in seen_paths_lines:
                continue
            seen_paths_lines.add(key)
            extra_chunks.append(related_chunk)
            if len(extra_chunks) >= max_extra:
                return chunks + extra_chunks

    return chunks + extra_chunks


if __name__ == "__main__":
    from retrieval.hybrid_search import hybrid_search

    query = "what does the after_request decorator do"
    results = hybrid_search(query, repo_name="pallets/flask")
    top_chunks = [chunk for chunk, score in results]

    expanded = expand_with_graph(top_chunks, repo_name="pallets/flask")

    print(f"Original chunks: {len(top_chunks)}, After graph expansion: {len(expanded)}\n")
    for c in expanded:
        print(f"{c.payload['path']} (lines {c.payload['start_line']}-{c.payload['end_line']})")