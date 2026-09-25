import { useEffect, useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { getTargets, runMonitor } from "../lib/api";

export default function Dashboard({ lastRun, setLastRun }) {
  const [count, setCount] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getTargets().then((t) => setCount(t.length)).catch((e) => setError(e.message));
  }, []);

  async function onRun() {
    setRunning(true);
    setError(null);
    try {
      const result = await runMonitor();
      setLastRun(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  const flagged = lastRun && lastRun.survivor_count > 0;
  const line = !lastRun
    ? "Ready when you are."
    : flagged
    ? `${lastRun.survivor_count} significant ${lastRun.survivor_count === 1 ? "change" : "changes"} flagged.`
    : "All quiet.";
  const sub = !lastRun
    ? "Run the monitor to check your watched pages for changes."
    : flagged
    ? "Review them on the Digest page."
    : "No significant changes across your watched pages.";

  return (
    <div className="wrap">
      <div className="page-head">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-sub">
          {count === null ? "Loading sources…" : `Watching ${count} ${count === 1 ? "source" : "sources"}.`}
        </p>
      </div>

      {error && <div className="banner banner-error">{error}</div>}

      <section className={`status${flagged ? " flagged" : ""}`}>
        <p className="status-line">{line}</p>
        <p className="status-sub">{sub}</p>
        <div className="run-row">
          <button className="btn btn-primary" onClick={onRun} disabled={running}>
            {running ? <Loader2 size={16} className="spin" /> : <Play size={16} />}
            {running ? "Running…" : "Run monitor"}
          </button>
        </div>
      </section>
    </div>
  );
}