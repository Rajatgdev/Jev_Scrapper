import { useState } from "react";
import { Routes, Route, NavLink, Navigate } from "react-router-dom";
import { LayoutDashboard, ListChecks, FileText, PanelLeftClose, PanelLeft } from "lucide-react";
import Dashboard from "./pages/Dashboard.jsx";
import Targets from "./pages/Targets.jsx";
import Digest from "./pages/Digest.jsx";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/targets", label: "Targets", icon: ListChecks },
  { to: "/digest", label: "Digest", icon: FileText },
];

export default function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [lastRun, setLastRun] = useState(null);

  return (
    <div className="shell">
      <aside className={`rail${collapsed ? " collapsed" : ""}`}>
        <div className="rail-head">
          <span className="mark-dot" />
          <span className="mark">Sentinel</span>
          <button
            className="rail-toggle"
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          >
            {collapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        <nav className="nav">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
              title={collapsed ? label : undefined}
            >
              <Icon size={18} />
              <span className="nav-label">{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="rail-foot">Changes classified by Jev</div>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard lastRun={lastRun} setLastRun={setLastRun} />} />
          <Route path="/targets" element={<Targets />} />
          <Route path="/digest" element={<Digest lastRun={lastRun} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}