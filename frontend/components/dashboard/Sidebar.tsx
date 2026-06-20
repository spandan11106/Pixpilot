import {
  GridIcon, ImageIcon, ModelIcon, BoltIcon,
} from "./icons";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">
          <BoltIcon width={20} height={20} stroke="#1B27B4" strokeWidth={2.2} />
        </span>
        <span className="brand-name">Pixpilot</span>
      </div>

      <nav className="nav-group">
        <a className="nav-item active" href="#"><GridIcon /> Workflow</a>
        <a className="nav-item" href="#"><ImageIcon /> Generations</a>
        <a className="nav-item" href="#"><ModelIcon /> Models</a>
      </nav>

      <div className="sidebar-foot">
        <div className="user-chip">
          <span className="avatar">AR</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--surface)" }}>Ava Renner</div>
            <div className="caption" style={{ color: "rgba(255,247,235,0.55)" }}>Workspace</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
