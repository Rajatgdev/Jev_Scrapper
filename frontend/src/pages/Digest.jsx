import { FileText } from "lucide-react";

export default function Digest({ lastRun }) {
  return (
    <div className="wrap">
      <div className="page-head">
        <h1 className="page-title">
          Digest
          {lastRun && (
            <span className="count-tag">
              {lastRun.survivor_count} flagged
            </span>
          )}
        </h1>
        <p className="page-sub">The most recent run's classified changes.</p>
      </div>

      {!lastRun ? (
        <div className="empty">
          <h3>Nothing to show yet</h3>
          <p>Run the monitor from the Dashboard, and the digest appears here.</p>
        </div>
      ) : (
        <div className={`digest${lastRun.survivor_count === 0 ? " digest-empty" : ""}`}>
          {lastRun.digest}
        </div>
      )}
    </div>
  );
}