import { useState } from "react";
import IndexPanel from "./components/IndexPanel";
import AskPanel from "./components/AskPanel";

export default function App() {
  const [indexedRepo, setIndexedRepo] = useState(null);

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="max-w-xl mx-auto">
        <h1 className="text-2xl font-semibold mb-1">Prism</h1>
        <p className="text-sm text-[var(--muted)] mb-8">
          Ask questions about any public GitHub repo.
        </p>
        <IndexPanel onIndexed={setIndexedRepo} />
        <AskPanel repo={indexedRepo} />
      </div>
    </div>
  );
}