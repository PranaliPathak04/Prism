from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from retrieval.hybrid_search import hybrid_search
from graph.expand import expand_with_graph
from generation.ask import ask_question
from storage.qdrant_store import index_repo, ensure_collection

from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job,JobStatus

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.arq = await create_pool(RedisSettings(host="localhost", port=6379))
    yield
    await app.state.arq.close()



app = FastAPI(title="Codebase RAG API"  ,lifespan=lifespan)


class AskRequest(BaseModel):
    question: str
    repo: str  # e.g. "pallets/flask"

class IndexRequest(BaseModel):
    owner: str
    repo: str
    branch: str = "main"


@app.get("/")
def root():
    return {"status": "ok", "message": "Codebase RAG API is running"}

@app.post("/index", status_code=202)
async def start_index(request: IndexRequest):
    redis = app.state.arq
    lock_key = f"lock:index:{request.owner}/{request.repo}"
    #one index job per repo at a time;expires on its own so a crash cant wedge it
    if not await redis.set(lock_key, "1", nx=True, ex=1800):  # 30 min lock
        raise HTTPException(status_code=409, detail="Indexing already in progress for this repo. Please try again later.")
    job = await redis.enqueue_job("index_repo_job", request.owner, request.repo, request.branch)
    return {"job_id": job.job_id, "status": "queued"}   
    
@app.get("/index/{job_id}")
async def index_status(job_id: str):
    job = Job(job_id, app.state.arq)
    status = await job.status()
    resp = {"job_id": job_id, "status": status.value}
    if status == JobStatus.complete:
        info = await job.result_info()
        resp["success"] = info.success
        resp["result"] = info.result if info.success else str (info.result)
    return resp

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