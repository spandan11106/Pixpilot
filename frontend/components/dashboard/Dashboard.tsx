"use client";

import "./dashboard.css";
import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { EmptyState } from "./EmptyState";
import { RunView } from "./RunView";
import { NewGenerationModal, type RunMeta } from "./NewGenerationModal";

export function Dashboard() {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeRun, setActiveRun] = useState<RunMeta | null>(null);

  return (
    <div className="pp-dash">
      <div className="app">
        <Sidebar />
        <div className="main">
          <Topbar onNewGeneration={() => setModalOpen(true)} />
          <main className="content">
            {activeRun ? (
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
