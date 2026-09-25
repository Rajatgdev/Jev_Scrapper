const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function req(path, opts = {}) {
  const r = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) {
    let msg = `${r.status}`;
    try {
      const body = await r.json();
      if (body.detail) msg = body.detail;
    } catch {}
    throw new Error(msg);
  }
  return r.json();
}

export const getTargets = () => req("/api/targets");
export const addTarget = (t) =>
  req("/api/targets", { method: "POST", body: JSON.stringify(t) });
export const updateTarget = (index, t) =>
  req(`/api/targets/${index}`, { method: "PUT", body: JSON.stringify(t) });
export const deleteTarget = (index) =>
  req(`/api/targets/${index}`, { method: "DELETE" });
export const runMonitor = () => req("/api/run", { method: "POST" });