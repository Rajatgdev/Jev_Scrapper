import { useState, useEffect } from "react";
import { runMonitor, getTargets } from "./lib/api";

export default function App() {
  const [targets, setTargets] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getTargets().then(setTargets).catch((e) => setError(e.message));
  }, []);

  async function onRun() {
    setLoading(true);
    setError(null);
    try {
      setResult(await runMonitor());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="wrap">
      <h1>Sentinel</h1>
      <p className="sub">Jev-driven website change monitor</p>

      <section>
        <h2>Watching {targets.length} page(s)</h2>
        <ul>
          {targets.map((t) => (
            <li key={t.url}>
              <strong>{t.title}</strong> — <span className="url">{t.url}</span>
            </li>
          ))}
        </ul>
      </section>

      <button onClick={onRun} disabled={loading}>
        {loading ? "Running…" : "Run monitor now"}
      </button>

      {error && <p className="err">Error: {error}</p>}

      {result && (
        <section className="result">
          <h2>Digest ({result.survivor_count} significant change(s))</h2>
          <pre>{result.digest}</pre>
        </section>
      )}
    </main>
  );
}
