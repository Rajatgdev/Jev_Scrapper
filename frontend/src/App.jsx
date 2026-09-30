import { Routes, Route, NavLink, Navigate } from "react-router-dom";
import { FileText, ListChecks, Settings as SettingsIcon, LogOut } from "lucide-react";
import Targets from "./pages/Targets.jsx";
import Digest from "./pages/Digest.jsx";
import Settings from "./pages/Settings.jsx";
import Login from "./pages/Login.jsx";
import { useAuth } from "./lib/auth";

const NAV = [
  { to: "/", label: "Digest", icon: FileText, end: true },
  { to: "/targets", label: "Targets", icon: ListChecks },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function App() {
  const { user, loading, logout } = useAuth();

  if (loading) return <div className="boot">Loading…</div>;
  if (!user) return <Login />;

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail-head">
          <span className="mark-dot" />
          <span className="mark">Sentinel</span>
        </div>

        <nav className="nav">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              <Icon size={18} className="nav-ico" />
              <span className="nav-label">{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="rail-foot">
          <button className="nav-item signout" onClick={logout}>
            <LogOut size={18} className="nav-ico" />
            <span className="nav-label">{user.email}</span>
          </button>
        </div>
      </aside>
      <div className="rail-spacer" />

      <main className="main">
        <Routes>
          <Route path="/" element={<Digest />} />
          <Route path="/targets" element={<Targets />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}