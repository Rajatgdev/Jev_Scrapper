import { useEffect, useState } from "react";
import { Check, Trash2, Loader2 } from "lucide-react";
import { getKeys, setKey, deleteKey, getSchedule, setSchedule } from "../lib/api";

const PROVIDERS = [
  { id: "openai", label: "OpenAI", hint: "Used to write the digest summaries. Starts with sk-…", where: "platform.openai.com/api-keys", url: "https://platform.openai.com/api-keys" },
  { id: "firecrawl", label: "Firecrawl", hint: "Used to scrape and diff your watched pages. Starts with fc-…", where: "firecrawl.dev/app/api-keys", url: "https://www.firecrawl.dev/app/api-keys" },
  { id: "jev", label: "Jev (TypeSafe)", hint: "Classifies every change by severity and relevance.", where: "console.typesafe.ai/keys", url: "https://console.typesafe.ai/keys" },
];

export default function Settings() {
  const [keys, setKeys] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    try { setKeys(await getKeys()); }
    catch (e) { setError(e.message); }
  }
  useEffect(() => { load(); }, []);

  return (
    <div className="wrap">
      <div className="page-head">
        <h1 className="page-title">Settings</h1>
        <p className="page-sub">
          Your API keys. Sentinel needs all three to run. Keys are encrypted, never shown again, and never leave the server.
        </p>
      </div>

      {error && <div className="banner banner-error">{error}</div>}

      <ScheduleCard />

      {keys === null ? (
        <div className="loading">Loading…</div>
      ) : (
        <div className="keys">
          {PROVIDERS.map((p) => (
            <KeyRow key={p.id} provider={p} state={keys[p.id]} onChanged={load} />
          ))}
        </div>
      )}
    </div>
  );
}

function KeyRow({ provider, state, onChanged }) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [rowError, setRowError] = useState(null);
  const configured = state?.configured;

  async function save() {
    if (!value.trim()) return;
    setBusy(true);
    setRowError(null);
    try {
      await setKey(provider.id, value.trim());
      setValue("");
      onChanged();
    } catch (e) {
      setRowError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setRowError(null);
    try {
      await deleteKey(provider.id);
      onChanged();
    } catch (e) {
      setRowError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="keyrow">
      <div className="keyrow-head">
        <div>
          <span className="keyrow-label">{provider.label}</span>
          {configured ? (
            <span className="keyrow-status ok">Configured · ••••{state.last4}</span>
          ) : (
            <span className="keyrow-status missing">Not set</span>
          )}
        </div>
        {configured && (
          <button className="icon-btn danger" onClick={remove} disabled={busy} aria-label="Remove key">
            <Trash2 size={16} />
          </button>
        )}
      </div>
      <p className="keyrow-hint">{provider.hint} <span className="keyrow-where">Get one at <a className="linklike" href={provider.url} target="_blank" rel="noreferrer noopener">{provider.where}</a>.</span></p>
      <div className="keyrow-input">
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={configured ? "Enter a new key to replace" : "Paste your key"}
          autoComplete="off"
        />
        <button className="btn btn-primary btn-sm" onClick={save} disabled={busy || !value.trim()}>
          {busy ? <Loader2 size={14} className="spin" /> : <Check size={14} />}
          {configured ? "Replace" : "Save"}
        </button>
      </div>
      {rowError && <p className="keyrow-error">{rowError}</p>}
    </div>
  );
}

const HOURS = Array.from({ length: 24 }, (_, h) => h);
const fmtHour = (h) => `${h % 12 === 0 ? 12 : h % 12}:00 ${h < 12 ? "AM" : "PM"}`;

function tzList() {
  try {
    if (typeof Intl.supportedValuesOf === "function") {
      return Intl.supportedValuesOf("timeZone");
    }
  } catch {}
  return ["UTC", "Europe/Dublin", "Europe/London", "America/New_York",
          "America/Los_Angeles", "Asia/Kolkata", "Asia/Tokyo", "Australia/Sydney"];
}

function ScheduleCard() {
  const [sched, setSched] = useState(null);
  const [hour, setHour] = useState(6);
  const [tz, setTz] = useState("Europe/Dublin");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);

  const zones = tzList();
  const options = zones.includes(tz) ? zones : [tz, ...zones];
  const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;

  useEffect(() => {
    getSchedule()
      .then((s) => { setSched(s); setHour(s.run_hour); setTz(s.timezone); })
      .catch((e) => setErr(e.message));
  }, []);

  async function save() {
    setBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const s = await setSchedule(hour, tz);
      setSched(s);
      setMsg(`Saved. Your digest runs daily at ${fmtHour(s.run_hour)} (${s.timezone}).`);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="keyrow schedule">
      <div className="keyrow-head">
        <span className="keyrow-label">Daily digest time</span>
        {sched && (
          <span className="keyrow-status ok">{fmtHour(sched.run_hour)} · {sched.timezone}</span>
        )}
      </div>
      <p className="keyrow-hint">
        Sentinel checks your pages and emails your digest once a day at this time.
        It can start up to an hour after the time you pick.
      </p>
      <div className="schedule-row">
        <select value={hour} onChange={(e) => setHour(Number(e.target.value))}>
          {HOURS.map((h) => <option key={h} value={h}>{fmtHour(h)}</option>)}
        </select>
        <select value={tz} onChange={(e) => setTz(e.target.value)}>
          {options.map((z) => <option key={z} value={z}>{z}</option>)}
        </select>
        <button className="btn btn-primary btn-sm" onClick={save} disabled={busy || !sched}>
          {busy ? <Loader2 size={14} className="spin" /> : <Check size={14} />}
          Save
        </button>
      </div>
      {browserTz && browserTz !== tz && (
        <p className="keyrow-hint">
          Your browser's timezone is {browserTz}.{" "}
          <button className="linklike" onClick={() => setTz(browserTz)}>Use it</button>
        </p>
      )}
      {msg && <p className="schedule-ok">{msg}</p>}
      {err && <p className="keyrow-error">{err}</p>}
    </div>
  );
}