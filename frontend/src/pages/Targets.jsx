import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, X, Check } from "lucide-react";
import { getTargets, addTarget, updateTarget, deleteTarget } from "../lib/api";

const BLANK = { title: "", url: "", question: "" };

export default function Targets() {
  const [targets, setTargets] = useState(null);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [editIndex, setEditIndex] = useState(null);
  const [draft, setDraft] = useState(BLANK);

  async function load() {
    try {
      setTargets(await getTargets());
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => { load(); }, []);

  function startAdd() {
    setDraft(BLANK);
    setEditIndex(null);
    setAdding(true);
  }
  function startEdit(i) {
    setDraft(targets[i]);
    setAdding(false);
    setEditIndex(i);
  }
  function cancel() {
    setAdding(false);
    setEditIndex(null);
    setDraft(BLANK);
    setError(null);
  }

  async function save() {
    setError(null);
    try {
      if (editIndex !== null) await updateTarget(editIndex, draft);
      else await addTarget(draft);
      cancel();
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function remove(i) {
    setError(null);
    try {
      await deleteTarget(i);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  const valid = draft.title.trim() && draft.url.trim() && draft.question.trim();

  return (
    <div className="wrap">
      <div className="page-head">
        <h1 className="page-title">Targets</h1>
        <p className="page-sub">
          The pages Sentinel watches. Each one has its own question that Jev uses to judge relevance.
        </p>
      </div>

      {error && <div className="banner banner-error">{error}</div>}

      {(adding || editIndex !== null) && (
        <div className="form-card">
          <div className="field">
            <label>Name</label>
            <input
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
              placeholder="Revenue — Customs Prohibitions"
            />
          </div>
          <div className="field">
            <label>Page URL</label>
            <input
              value={draft.url}
              onChange={(e) => setDraft({ ...draft, url: e.target.value })}
              placeholder="https://www.revenue.ie/…"
            />
          </div>
          <div className="field">
            <label>Relevance question</label>
            <input
              value={draft.question}
              onChange={(e) => setDraft({ ...draft, question: e.target.value })}
              placeholder="Is this change about customs rules for chemical products?"
            />
            <p className="hint">
              Jev answers this for every change on the page. Keep it a yes/no question specific to what you care about here.
            </p>
          </div>
          <div className="form-actions">
            <button className="btn btn-primary btn-sm" onClick={save} disabled={!valid}>
              <Check size={15} /> {editIndex !== null ? "Save changes" : "Add target"}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={cancel}>
              <X size={15} /> Cancel
            </button>
          </div>
        </div>
      )}

      {!adding && editIndex === null && (
        <button className="btn btn-ghost" onClick={startAdd} style={{ marginBottom: 24 }}>
          <Plus size={16} /> Add a target
        </button>
      )}

      {targets === null ? (
        <div className="loading">Loading targets…</div>
      ) : targets.length === 0 ? (
        <div className="empty">
          <h3>No targets yet</h3>
          <p>Add a page to start watching it for changes.</p>
        </div>
      ) : (
        <div className="tlist">
          {targets.map((t, i) => (
            <div className="titem" key={t.url + i}>
              <div className="titem-body">
                <p className="titem-title">{t.title}</p>
                <p className="titem-url">{t.url}</p>
                <div className="titem-q">
                  <span className="q-mark">asks</span>
                  <span>{t.question}</span>
                </div>
              </div>
              <div className="titem-actions">
                <button className="icon-btn" onClick={() => startEdit(i)} aria-label="Edit">
                  <Pencil size={16} />
                </button>
                <button className="icon-btn danger" onClick={() => remove(i)} aria-label="Delete">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}