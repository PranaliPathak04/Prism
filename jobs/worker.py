import asyncio
from arq import Retry
from arq.connections import RedisSettings

MAX_TRIES = 3  # Maximum number of retries for a job

async def index_repo_job(ctx,owner : str, repo : str, branch : str = "main"):
    """
    Fetches a GitHub repo, chunks its files, embeds them, and stores them in Qdrant.
    Full pipeline: fetch -> chunk -> embed -> store vectors -> extract & store call graph.
    Returns a summary dict.
    """
    from storage.qdrant_store import index_repo 
    lock_key = f"lock:index:{owner}/{repo}"
    try:
        #index_repo is a long-running task, so we use a lock to prevent concurrent indexing of the same repo
        #index_repo is sync and CPU-heavy; run it in a thread so the worker's event loop stays alive
        result = await asyncio.to_thread(index_repo, owner, repo, branch)
    except Exception:
        if ctx["job_try"] < MAX_TRIES:
            raise Retry(defer=ctx["job_try"] * 10)  # Retry after 10 seconds then 20 seconds, etc.
        await ctx["redis"].delete(lock_key)  # Ensure lock is released on failure
        raise


    await ctx["redis"].delete(lock_key)  # Release the lock after processing
    return result

class WorkerSettings:
    functions = [index_repo_job]
    redis_settings = RedisSettings(host="localhost", port=6379)
    max_tries = MAX_TRIES  # Set the maximum number of retries for all jobs
    job_timeout = 1800 # 30 min cap per job
    keep_result = 86400  # keep status/result for 24h so polling works
