import { useState, useEffect, useRef } from "react";
import { startIndex, getIndexStatus } from "../api/client";

export default function IndexPanel({ onIndexed }) {
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [branch, setBranch] = useState("main");
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    return () => clearInterval(pollRef.current);
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setStatus(null);
    try {
      const { job_id } = await startIndex(owner, repo, branch);
      setJobId(job_id);
      setStatus({ status: "queued" });
      pollRef.current = setInterval(async () => {
        try {
          const result = await getIndexStatus(job_id);
          setStatus(result);
          if (result.status === "complete") {
            clearInterval(pollRef.current);
            if (result.success) onIndexed(`${owner}/${repo}`);
          }
        } catch (err) {
          clearInterval(pollRef.current);
          setError(err.message);
        }
      }, 2500);
    } catch (err) {
      setError(err.message);
    }
  }

  const isRunning = status && status.status !== "complete";

  return (
    <section className="border border-[var(--border)] rounded-lg p-6">
      <h2 className="text-lg font-medium mb-4">Index a repository</h2>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
        <input
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          placeholder="owner"
          disabled={isRunning}
          className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded px-3 py-2 text-sm"
          required
        />
        <input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="repo"
          disabled={isRunning}
          className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded px-3 py-2 text-sm"
          required
        />
        <input
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="branch"
          disabled={isRunning}
          className="w-24 bg-[var(--surface)] border border-[var(--border)] rounded px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={isRunning}
          className="px-4 py-2 rounded bg-[var(--text)] text-[var(--bg)] text-sm font-medium disabled:opacity-40"
        >
          Index
        </button>
      </form>

      {isRunning && <div className="prism-bar rounded-full mb-3" />}

      {status && (
        <p className="text-sm text-[var(--muted)]">
          {status.status === "complete"
            ? status.success
              ? `Done — ${status.result.files_changed} changed, ${status.result.files_unchanged} unchanged, ${status.result.chunks_stored} chunks stored.`
              : `Failed: ${status.result}`
            : `Status: ${status.status}`}
        </p>
      )}
      {error && <p className="text-sm text-red-400">{error}</p>}
    </section>
  );
}