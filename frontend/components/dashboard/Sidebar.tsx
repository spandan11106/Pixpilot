import {
  GridIcon, ImageIcon, ModelIcon, BoltIcon,
} from "./icons";

export type AppView = "workflow" | "generations";

interface SidebarProps {
  activeView: AppView;
  onViewChange: (view: AppView) => void;
}

export function Sidebar({ activeView, onViewChange }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">
          <BoltIcon width={20} height={20} stroke="#1B27B4" strokeWidth={2.2} />
        </span>
        <span className="brand-name">Pixpilot</span>
      </div>

      <nav className="nav-group">
        <button
          className={`nav-item${activeView === "workflow" ? " active" : ""}`}
          onClick={() => onViewChange("workflow")}
        >
          <GridIcon /> Workflow
        </button>
        <button
          className={`nav-item${activeView === "generations" ? " active" : ""}`}
          onClick={() => onViewChange("generations")}
        >
          <ImageIcon /> Generations
        </button>
        <button className="nav-item" disabled>
          <ModelIcon /> Models
        </button>
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
