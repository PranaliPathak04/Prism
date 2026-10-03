import { useState } from "react";
import { askQuestion } from "../api/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function AskPanel({ repo }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await askQuestion(question, repo);
      setAnswer(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const disabled = !repo;

  return (
    <section
      className={`border border-[var(--border)] rounded-lg p-6 mt-6 transition-opacity ${
        disabled ? "opacity-40 pointer-events-none" : ""
      }`}
    >
      <h2 className="text-lg font-medium mb-1">Ask</h2>
      <p className="text-sm text-[var(--muted)] mb-4">
        {repo ? `Querying ${repo}` : "Index a repo first"}
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="what does the after_request decorator do"
          className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded px-3 py-2 text-sm"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 rounded bg-[var(--text)] text-[var(--bg)] text-sm font-medium disabled:opacity-40"
        >
          {loading ? "..." : "Ask"}
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {answer && (
        <div>
          <div className="text-sm leading-relaxed mb-4 prose prose-invert prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer.answer}</ReactMarkdown>
            </div>
          <div className="space-y-1">
            {answer.sources.map((s, i) => (
              <div key={i} className="text-xs font-mono-path text-[var(--muted)]">
                {s.path}:{s.start_line}-{s.end_line}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}