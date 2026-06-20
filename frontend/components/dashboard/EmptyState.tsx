import { PlusIcon } from "./icons";

export function EmptyState({ onNewGeneration }: { onNewGeneration: () => void }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
      </div>
      <h2 className="heading-2">No active run</h2>
      <p className="empty-sub">Start a new generation to see the pipeline in action.</p>
      <button className="btn btn-cta" onClick={onNewGeneration}>
        <PlusIcon /> New Generation
      </button>
    </div>
  );
}
