import { SearchIcon, BellIcon, DownloadIcon, PlusIcon } from "./icons";

export function Topbar() {
  return (
    <header className="topbar">
      <div className="search">
        <SearchIcon />
        <input type="text" placeholder="Search prompts, jobs, models…" />
      </div>
      <div className="topbar-actions">
        <button className="icon-btn" aria-label="Notifications">
          <BellIcon />
          <span className="dot" />
        </button>
        <button className="btn btn-outline btn-sm"><DownloadIcon /> Export</button>
        <button className="btn btn-cta"><PlusIcon /> New Generation</button>
      </div>
    </header>
  );
}
