// Same-origin: Vercel proxies /api/* to the Railway backend, so we use relative
// paths and send the session cookie with every request.
async function req(path, opts = {}) {
  const r = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) {
    let msg = `${r.status}`;
    try {
      const body = await r.json();
      if (typeof body.detail === "string") {
        msg = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI validation errors: array of {msg, loc, ...}
        msg = body.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
      } else if (body.detail) {
        msg = JSON.stringify(body.detail);
      }
    } catch {}
    const err = new Error(msg);
    err.status = r.status;
    throw err;
  }
  return r.json();
}

// auth
export const signup = (email, password) =>
  req("/api/auth/signup", { method: "POST", body: JSON.stringify({ email, password }) });
export const login = (email, password) =>
  req("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
export const logout = () => req("/api/auth/logout", { method: "POST" });
export const getMe = () => req("/api/auth/me");

// targets
export const getTargets = () => req("/api/targets");
export const addTarget = (t) =>
  req("/api/targets", { method: "POST", body: JSON.stringify(t) });
export const updateTarget = (id, t) =>
  req(`/api/targets/${id}`, { method: "PUT", body: JSON.stringify(t) });
export const deleteTarget = (id) =>
  req(`/api/targets/${id}`, { method: "DELETE" });
export const runMonitor = () => req("/api/run", { method: "POST" });
export const getDigest = () => req("/api/digest");

// api keys (Settings)
export const getKeys = () => req("/api/keys");
export const setKey = (provider, key) =>
  req(`/api/keys/${provider}`, { method: "PUT", body: JSON.stringify({ key }) });
export const deleteKey = (provider) =>
  req(`/api/keys/${provider}`, { method: "DELETE" });

// schedule (Settings)
export const getSchedule = () => req("/api/schedule");
export const setSchedule = (run_hour, timezone) =>
  req("/api/schedule", { method: "PUT", body: JSON.stringify({ run_hour, timezone }) });