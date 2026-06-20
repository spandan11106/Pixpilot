import { SearchIcon, BellIcon, DownloadIcon } from "./icons";
import { NewGeneration } from "./NewGeneration";
import { ThemeToggle } from "./ThemeToggle";

export function Topbar({ onNewGeneration }: { onNewGeneration: () => void }) {
  return (
    <header className="topbar">
      <div className="search">
        <SearchIcon />
        <input type="text" placeholder="Search prompts, jobs, models…" />
      </div>
      <div className="topbar-actions">
        <ThemeToggle />
        <button className="icon-btn" aria-label="Notifications">
          <BellIcon />
          <span className="dot" />
        </button>
        <button className="btn btn-outline btn-sm"><DownloadIcon /> Export</button>
        <NewGeneration onClick={onNewGeneration} />
      </div>
    </header>
  );
}
