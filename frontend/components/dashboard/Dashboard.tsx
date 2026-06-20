"use client";

import "./dashboard.css";
import { useState } from "react";
import { Sidebar, type AppView } from "./Sidebar";
import { Topbar } from "./Topbar";
import { EmptyState } from "./EmptyState";
import { RunView } from "./RunView";
import { NewGenerationModal, type RunMeta } from "./NewGenerationModal";
import { GenerationsPage } from "./GenerationsPage";

export function Dashboard() {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeRun, setActiveRun] = useState<RunMeta | null>(null);
  const [view, setView] = useState<AppView>("workflow");

  return (
    <div className="pp-dash">
      <div className="app">
        <Sidebar activeView={view} onViewChange={setView} />
        <div className="main">
          <Topbar onNewGeneration={() => setModalOpen(true)} />
          <main className="content">
            {view === "generations" ? (
              <GenerationsPage />
            ) : activeRun ? (
              <RunView run={activeRun} onDismiss={() => setActiveRun(null)} />
            ) : (
              <EmptyState onNewGeneration={() => setModalOpen(true)} />
            )}
          </main>
        </div>
      </div>

      {modalOpen && (
        <NewGenerationModal
          onClose={() => setModalOpen(false)}
          onRunStart={(meta) => {
            setActiveRun(meta);
            setModalOpen(false);
          }}
        />
      )}
    </div>
  );
}
