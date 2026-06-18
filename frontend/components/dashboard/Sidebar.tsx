import {
  GridIcon, ActivityIcon, ImageIcon, MessageIcon, ModelIcon,
  ChartIcon, SettingsIcon, BoltIcon,
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
        <a className="nav-item active" href="#"><GridIcon /> Overview</a>
        <a className="nav-item" href="#"><ActivityIcon /> Pipeline <span className="count">3</span></a>
        <a className="nav-item" href="#"><ImageIcon /> Generations</a>
        <a className="nav-item" href="#"><MessageIcon /> Prompts</a>
        <a className="nav-item" href="#"><ModelIcon /> Models</a>
      </nav>

      <nav className="nav-group">
        <div className="nav-heading overline">Workspace</div>
        <a className="nav-item" href="#"><ChartIcon /> Analytics</a>
        <a className="nav-item" href="#"><SettingsIcon /> Settings</a>
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
