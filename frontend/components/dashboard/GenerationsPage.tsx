"use client";

import { useEffect, useState } from "react";
import { GenerationDetailModal } from "./GenerationDetailModal";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface RunSummary {
  run_id: string;
  generation_name: string;
  created_at: string;
  status: string;
  pipeline_mode: string;
  inputs: {
    image_path?: string;
    [key: string]: unknown;
  };
  ingestion?: {
    video_frame_count?: number;
    model_3d_thumbnail_count?: number;
    image_processed?: boolean;
  };
}

const MODE_LABELS: Record<string, string> = {
  ecommerce: "E-Commerce",
  social: "Social Media",
  ab: "A/B Exploration",
  seasonal: "Seasonal",
  summarize: "Summarization",
};

function statusClass(status: string) {
  if (status === "completed") return "badge-success";
  if (status === "running") return "badge-amber";
  return "badge-error";
}

function RunCard({ run, onClick }: { run: RunSummary; onClick: () => void }) {
  const imageFilename = run.inputs.image_path?.split("/").pop();
  const thumbUrl = imageFilename
    ? `${API_URL}/api/runs/${run.run_id}/inputs/${imageFilename}`
    : null;

  const date = new Date(run.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <button className="gen-card" onClick={onClick}>
      <div className="gen-card-thumb">
        {thumbUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumbUrl} alt={run.generation_name} className="gen-card-img" />
        ) : (
          <div className="gen-card-placeholder">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
          </div>
        )}
      </div>
      <div className="gen-card-body">
        <div className="gen-card-name">{run.generation_name}</div>
        <div className="gen-card-meta">
          <span className={`badge ${statusClass(run.status)}`} style={{ fontSize: 11 }}>
            {run.status}
          </span>
          <span className="gen-card-mode">{MODE_LABELS[run.pipeline_mode] ?? run.pipeline_mode}</span>
        </div>
        <div className="gen-card-date">{date}</div>
      </div>
    </button>
  );
}

export function GenerationsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<RunSummary | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/runs`)
      .then((r) => r.json())
      .then((data) => { setRuns(data); setLoading(false); })
      .catch(() => { setError("Failed to load generations."); setLoading(false); });
  }, []);

  if (loading) {
    return (
      <div className="gen-page-empty">
        <span className="spinner" style={{ width: 24, height: 24, borderWidth: 2 }} />
        Loading generations…
      </div>
    );
  }

  if (error) {
    return <div className="gen-page-empty gen-page-error">{error}</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="gen-page-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{ opacity: 0.3 }}>
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
        <p style={{ marginTop: 12, color: "var(--muted-fg)" }}>No generations yet. Start one from the Workflow tab.</p>
      </div>
    );
  }

  return (
    <div className="gen-page">
      <div className="gen-page-header">
        <h1 className="heading-2">Generations</h1>
        <span className="caption" style={{ color: "var(--muted-fg)" }}>{runs.length} run{runs.length !== 1 ? "s" : ""}</span>
      </div>

      <div className="gen-grid">
        {runs.map((run) => (
          <RunCard key={run.run_id} run={run} onClick={() => setSelected(run)} />
        ))}
      </div>

      {selected && (
        <GenerationDetailModal
          run={selected}
          onClose={() => setSelected(null)}
          onDeleted={() => {
            setRuns((prev) => prev.filter((r) => r.run_id !== selected.run_id));
            setSelected(null);
          }}
        />
      )}
    </div>
  );
}
