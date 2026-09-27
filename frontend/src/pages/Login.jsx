import { useState } from "react";
import { useAuth } from "../lib/auth";

export default function Login() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState("login"); // login | signup
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const isSignup = mode === "signup";

  async function submit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (isSignup) await signup(email, password);
      else await login(email, password);
      // AuthProvider sets the user; the router swaps to the app automatically.
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="mark-dot" />
          <span className="mark">Sentinel</span>
        </div>
        <h1 className="auth-title">
          {isSignup ? "Create your account" : "Welcome back"}
        </h1>
        <p className="auth-sub">
          {isSignup
            ? "Start watching pages for the changes that matter."
            : "Sign in to your monitor."}
        </p>

        <form onSubmit={submit}>
          <div className="field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isSignup ? "At least 8 characters" : "Your password"}
              autoComplete={isSignup ? "new-password" : "current-password"}
              required
            />
          </div>

          {error && <div className="banner banner-error">{error}</div>}

          <button className="btn btn-primary auth-submit" disabled={busy}>
            {busy ? "…" : isSignup ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="auth-switch">
          {isSignup ? "Already have an account?" : "New here?"}{" "}
          <button
            className="linklike"
            onClick={() => { setMode(isSignup ? "login" : "signup"); setError(null); }}
          >
            {isSignup ? "Sign in" : "Create one"}
          </button>
        </p>
      </div>
    </div>
  );
}