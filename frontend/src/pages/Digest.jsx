import { useEffect, useRef, useState } from "react";
import { Play, FileText, ExternalLink, X } from "lucide-react";
import { getDigest, runMonitor } from "../lib/api";

const SEV_LABEL = { high: "High significance", medium: "Medium significance", low: "Low significance" };

export default function Digest() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState(null); // index into changes
  const [panelW, setPanelW] = useState(440);
  const scrollerRef = useRef(null);
  const barRef = useRef(null);
  const draggingRef = useRef(false);

  useEffect(() => {
    getDigest().then(setData).catch((e) => setError(e.message));
  }, []);

  // scroll-linked morph: set --p (0..1) on the scroller
  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const START = 10, END = 150;
    const onScroll = () => {
      const p = Math.max(0, Math.min(1, (el.scrollTop - START) / (END - START)));
      el.parentElement.style.setProperty("--p", p.toFixed(3));
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => el.removeEventListener("scroll", onScroll);
  }, [data]);

  // panel resize
  useEffect(() => {
    const onMove = (e) => {
      if (!draggingRef.current) return;
      setPanelW(Math.max(320, Math.min(760, window.innerWidth - e.clientX)));
    };
    const onUp = () => {
      draggingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
  }, []);

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") setSelected(null); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  async function onRun() {
    setRunning(true);
    setError(null);
    const prevFinished = data?.finished_at || null;
    try {
      await runMonitor(); // returns immediately; work runs in background
      // poll /api/digest until a NEW run lands (finished_at changes)
      const started = Date.now();
      const TIMEOUT = 3 * 60 * 1000; // 3 min ceiling
      while (Date.now() - started < TIMEOUT) {
        await new Promise((r) => setTimeout(r, 4000));
        const fresh = await getDigest();
        if (fresh.finished_at && fresh.finished_at !== prevFinished) {
          setData(fresh);
          setSelected(null);
          return;
        }
      }
      setData(await getDigest());
      setError("The run is taking longer than expected — showing the latest available.");
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  if (error && !data) {
    return <div className="wrap"><h1 className="page-title">Digest</h1><div className="banner banner-error">{error}</div></div>;
  }
  if (!data) {
    return <div className="wrap"><div className="loading">Loading…</div></div>;
  }

  const { briefing, changes, total, finished_at, source_count, keys_configured } = data;
  const when = finished_at ? new Date(finished_at).toLocaleString() : null;
  const sel = selected != null ? changes[selected] : null;

  return (
    <div className="digest-root" style={{ "--panel-w": panelW + "px" }}>
      <div className="list-col" ref={scrollerRef}>
        <div className="wrap wide">
          <div className="morphwrap" />

          <h1 className="page-title">Today's changes</h1>
          <p className="page-sub">
            {total === 0
              ? "No changes in the latest run"
              : `${total} change${total === 1 ? "" : "s"} across your ${source_count} source${source_count === 1 ? "" : "s"}`}
            {when ? ` · ${when}` : ""}
          </p>

          {!keys_configured && (
            <div className="banner banner-warn">
              Add your OpenAI, Firecrawl and Jev keys in{" "}
              <a href="/settings">Settings</a> to start monitoring.
            </div>
          )}
          {error && <div className="banner banner-error">{error}</div>}

          {total === 0 ? (
            <div className="empty">
              <h3>All quiet</h3>
              <p>Nothing changed across your watched pages in the last run.</p>
            </div>
          ) : (
            <>
              {briefing && (
                <div className="brief">
                  <p className="brief-label">Briefing</p>
                  <p>{briefing}</p>
                </div>
              )}
              <div className="list-head">
                <h2 className="list-title">What changed</h2>
                <span className="list-note">Tap any item for detail</span>
              </div>
              <div className="changes">
                {changes.map((c, i) => (
                  <div
                    key={i}
                    className={`change${selected === i ? " selected" : ""}`}
                    style={{ animationDelay: `${0.04 * i}s` }}
                    onClick={() => setSelected(i)}
                  >
                    <span className={`sev-dot ${c.severity}`} />
                    <div className="change-body">
                      <p className="change-summary">{c.summary}</p>
                      <div className="change-meta">{c.page_title}</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* morphing status bar */}
      <div className="bar" ref={barRef}>
        <span className="notch-status">
          <span className="notch-dot" />
          {source_count} source{source_count === 1 ? "" : "s"}
        </span>
        <div className="bar-items">
          <div className="strip-item">
            <FileText size={16} className="strip-ico" />
            <div><div className="strip-k">Watching</div><div className="strip-v">{source_count} source{source_count === 1 ? "" : "s"}</div></div>
          </div>
          {when && (
            <div className="strip-item">
              <span className="strip-ico" />
              <div><div className="strip-k">Last run</div><div className="strip-v">{when}</div></div>
            </div>
          )}
        </div>
        <button className="run-btn" onClick={onRun} disabled={running || !keys_configured}
          title={!keys_configured ? "Add your API keys in Settings to run" : undefined}>
          <Play size={15} />
          {running ? "Running…" : "Run now"}
        </button>
      </div>

      {/* resizer + detail panel */}
      <div
        className="resizer"
        onMouseDown={(e) => {
          if (selected == null) return;
          draggingRef.current = true;
          document.body.style.cursor = "col-resize";
          document.body.style.userSelect = "none";
          e.preventDefault();
        }}
      />
      <div className={`scrim${sel ? " show" : ""}`} onClick={() => setSelected(null)} />
      <aside className={`detail${sel ? " open" : ""}`}>
        {sel && (
          <>
            <button className="detail-close" onClick={() => setSelected(null)} aria-label="Close"><X size={18} /></button>
            <div className="detail-inner">
              <div className="d-sev-row"><span className={`d-sev-dot ${sel.severity}`} /><span className="d-sev-txt">{SEV_LABEL[sel.severity]}</span></div>
              <h2 className="d-title">{sel.summary}</h2>
              <p className="d-src"><FileText size={14} />{sel.page_title}</p>
              {sel.detail && (
                <div className="d-section">
                  <p className="d-h">What changed</p>
                  <p className="d-body">{sel.detail}</p>
                </div>
              )}
              {sel.quote && (
                <div className="d-section">
                  <p className="d-h">On the page now</p>
                  <div className="d-quote"><span className="newtag">New content</span>{sel.quote}</div>
                </div>
              )}
              <a className="d-visit" href={sel.item_url || sel.page_url} target="_blank" rel="noreferrer">
                Open the live page <ExternalLink size={14} />
              </a>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}