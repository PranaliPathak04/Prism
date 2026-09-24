from fastapi import FastAPI
from pydantic import BaseModel

from retrieval.hybrid_search import hybrid_search
from graph.expand import expand_with_graph
from generation.ask import ask_question

app = FastAPI(title="Codebase RAG API")


class AskRequest(BaseModel):
    question: str
    repo: str  # e.g. "pallets/flask"


@app.get("/")
def root():
    return {"status": "ok", "message": "Codebase RAG API is running"}


@app.post("/ask")
def ask(request: AskRequest):
    results = hybrid_search(request.question, repo_name=request.repo)
    top_chunks = [chunk for chunk, score in results]

    expanded_chunks = expand_with_graph(top_chunks, repo_name=request.repo)

    answer = ask_question(request.question, expanded_chunks)

    sources = [
        {
            "path": c.payload["path"],
            "start_line": c.payload["start_line"],
            "end_line": c.payload["end_line"],
        }
        for c in expanded_chunks
    ]

    return {
        "question": request.question,
        "answer": answer,
        "sources": sources,
    }