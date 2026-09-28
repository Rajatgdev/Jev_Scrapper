import { useEffect, useState } from "react";
import { getDigest } from "../lib/api";

const TABS = [
  { key: "all", label: "All" },
  { key: "high", label: "High" },
  { key: "medium", label: "Medium" },
  { key: "low", label: "Low" },
];

const SEV_CLASS = { high: "sev-high", medium: "sev-medium", low: "sev-low" };

export default function Digest() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("all");

  useEffect(() => {
    getDigest().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="wrap">
        <div className="page-head"><h1 className="page-title">Digest</h1></div>
        <div className="banner banner-error">{error}</div>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="wrap">
        <div className="page-head"><h1 className="page-title">Digest</h1></div>
        <div className="loading">Loading…</div>
      </div>
    );
  }

  const { changes, counts, total, finished_at } = data;
  const shown = tab === "all" ? changes : changes.filter((c) => c.severity === tab);
  const when = finished_at ? new Date(finished_at).toLocaleString() : null;

  return (
    <div className="wrap">
      <div className="page-head">
        <h1 className="page-title">Digest</h1>
        <p className="page-sub">
          {total === 0
            ? "No changes in the latest run."
            : `${total} change${total === 1 ? "" : "s"} from the latest run`}
          {when ? ` · ${when}` : ""}
        </p>
      </div>

      {total === 0 ? (
        <div className="empty">
          <h3>All quiet</h3>
          <p>Nothing changed across your watched pages in the last run.</p>
        </div>
      ) : (
        <>
          <div className="tabs">
            {TABS.map((t) => {
              const n = t.key === "all" ? total : counts[t.key];
              return (
                <button
                  key={t.key}
                  className={`tab${tab === t.key ? " active" : ""}`}
                  onClick={() => setTab(t.key)}
                >
                  {t.label} <span className="tab-count">{n}</span>
                </button>
              );
            })}
          </div>

          <div className="changes">
            {shown.length === 0 ? (
              <p className="empty-tab">No {tab} changes.</p>
            ) : (
              shown.map((c, i) => (
                <div className="change" key={i}>
                  <span className={`sev-dot ${SEV_CLASS[c.severity]}`} />
                  <div className="change-body">
                    <p className="change-summary">{c.summary}</p>
                    <a className="change-page" href={c.page_url}
                       target="_blank" rel="noreferrer">
                      {c.page_title}
                    </a>
                  </div>
                  <span className={`sev-label ${SEV_CLASS[c.severity]}`}>
                    {c.severity}
                  </span>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}