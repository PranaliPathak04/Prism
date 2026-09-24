from graph.expand import expand_with_graph
from retrieval.hybrid_search import hybrid_search

query = "what does the after_request decorator do"
results = hybrid_search(query, repo_name="pallets/flask")
top_chunks = [chunk for chunk, score in results]
expanded = expand_with_graph(top_chunks, repo_name="pallets/flask")

for c in expanded:
    print(f"\n--- {c.payload['path']} (lines {c.payload['start_line']}-{c.payload['end_line']}) ---")
    print(c.payload["content"][:250])