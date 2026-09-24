const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function runMonitor() {
  const r = await fetch(`${API_URL}/api/run`, { method: "POST" });
  if (!r.ok) throw new Error(`run failed: ${r.status}`);
  return r.json();
}

export async function getTargets() {
  const r = await fetch(`${API_URL}/api/targets`);
  if (!r.ok) throw new Error(`targets failed: ${r.status}`);
  return r.json();
}
