"use client";

import { useEffect, useState } from "react";
import { XIcon } from "./icons";
import { Lightbox } from "./Lightbox";
import type { RunSummary } from "./GenerationsPage";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Tab = "inputs" | "processed" | "vision" | "summary" | "imagegen";

const TABS: { id: Tab; label: string }[] = [
  { id: "inputs",   label: "Inputs" },
  { id: "processed", label: "Processed" },
  { id: "vision",   label: "Vision" },
  { id: "summary",  label: "Summary" },
  { id: "imagegen", label: "Image Gen" },
];

const MODE_LABELS: Record<string, string> = {
  ecommerce: "E-Commerce Batch",
  social: "Social Media",
  ab: "A/B Exploration",
  seasonal: "Seasonal Campaign",
  summarize: "Summarization",
};

// ── Inputs Tab ────────────────────────────────────────────────────────────────

function InputsTab({ run, onZoom }: { run: RunSummary; onZoom: (src: string) => void }) {
  const imageFilename = run.inputs.image_path?.split("/").pop();
  const thumbUrl = imageFilename
    ? `${API_URL}/api/runs/${run.run_id}/inputs/${imageFilename}`
    : null;

  const fields = [
    { label: "Product description", key: "description_product" },
    { label: "Target audience",     key: "description_audience" },
    { label: "Color palette",       key: "description_colors" },
  ];

  const meta = run as unknown as Record<string, unknown>;
  const steering = (meta.steering ?? {}) as Record<string, unknown>;
  const supervision = (meta.supervision ?? {}) as Record<string, unknown>;

  return (
    <div className="gd-tab-body">
      {thumbUrl && (
        <div className="gd-section">
          <div className="gd-section-title">Product Image</div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={thumbUrl} alt="Product" className="gd-product-img gd-zoomable" onClick={() => onZoom(thumbUrl)} />
        </div>
      )}

      <div className="gd-section">
        <div className="gd-section-title">Descriptions</div>
        <div className="gd-kv-list">
          {fields.map(({ label, key }) => (
            (run.inputs[key] as string) ? (
              <div key={key} className="gd-kv-row">
                <span className="gd-kv-label">{label}</span>
                <span className="gd-kv-value">{run.inputs[key] as string}</span>
              </div>
            ) : null
          ))}
        </div>
      </div>

      <div className="gd-section">
        <div className="gd-section-title">Pipeline Settings</div>
        <div className="gd-kv-list">
          <div className="gd-kv-row">
            <span className="gd-kv-label">Mode</span>
            <span className="gd-kv-value">{MODE_LABELS[run.pipeline_mode] ?? run.pipeline_mode}</span>
          </div>
          {Object.entries(steering).map(([k, v]) =>
            v ? (
              <div key={k} className="gd-kv-row">
                <span className="gd-kv-label">{k.replace(/_/g, " ")}</span>
                <span className="gd-kv-value">{String(v)}</span>
              </div>
            ) : null
          )}
          <div className="gd-kv-row">
            <span className="gd-kv-label">Research supervision</span>
            <span className="gd-kv-value">{supervision.research ? "Enabled" : "Disabled"}</span>
          </div>
          <div className="gd-kv-row">
            <span className="gd-kv-label">Image gen supervision</span>
            <span className="gd-kv-value">{supervision.image_gen ? "Enabled" : "Disabled"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Processed Tab ─────────────────────────────────────────────────────────────

interface IngestionData {
  text?: Record<string, { status: string; content: string; metrics: Record<string, unknown> }>;
  image?: { status: string; filename: string; metrics: Record<string, unknown>; image_payload?: string };
  reference_image?: { status: string; filename: string; metrics: Record<string, unknown>; image_payload?: string };
  video?: { status: string; frame_count?: number; frames?: Array<{ frame_index: number; image_payload?: string; metrics?: Record<string, unknown> }> };
  model_3d?: { status: string; thumbnail_count?: number; thumbnails?: Array<{ view: string; image_payload?: string }> };
}

function ProcessedTab({ runId, onZoom }: { runId: string; onZoom: (src: string) => void }) {
  const [data, setData] = useState<IngestionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/runs/${runId}/ingestion`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => { setError("Failed to load ingestion data."); setLoading(false); });
  }, [runId]);

  if (loading) return (
    <div className="gd-tab-loading">
      <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
      Loading processed data…
    </div>
  );
  if (error) return <div className="gd-tab-error">{error}</div>;
  if (!data) return null;

  return (
    <div className="gd-tab-body">
      {data.text && (
        <div className="gd-section">
          <div className="gd-section-title">Text Fields</div>
          <div className="gd-kv-list">
            {Object.entries(data.text).map(([field, val]) => (
              <div key={field} className="gd-kv-row">
                <span className="gd-kv-label">{field}</span>
                <span className="gd-kv-value">{val.content}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.image?.image_payload && (
        <div className="gd-section">
          <div className="gd-section-title">
            Product Image
            {data.image.metrics && (
              <span className="gd-section-meta">
                {String(data.image.metrics.processed_resolution)} ·{" "}
                {String(data.image.metrics.payload_size_kb)} KB
              </span>
            )}
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={data.image.image_payload} alt="Processed product" className="gd-product-img gd-zoomable" onClick={() => onZoom(data.image!.image_payload!)} />
        </div>
      )}

      {data.reference_image?.image_payload && (
        <div className="gd-section">
          <div className="gd-section-title">Reference Image</div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={data.reference_image.image_payload} alt="Reference" className="gd-product-img gd-zoomable" onClick={() => onZoom(data.reference_image!.image_payload!)} />
        </div>
      )}

      {data.video?.frames && data.video.frames.length > 0 && (
        <div className="gd-section">
          <div className="gd-section-title">
            Video Frames
            <span className="gd-section-meta">{data.video.frames.length} extracted</span>
          </div>
          <div className="gd-frame-grid">
            {data.video.frames.filter((f) => f.image_payload).map((frame) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={frame.frame_index}
                src={frame.image_payload!}
                alt={`Frame ${frame.frame_index}`}
                className="gd-frame-thumb gd-zoomable"
                title={`Frame ${frame.frame_index}`}
                onClick={() => onZoom(frame.image_payload!)}
              />
            ))}
          </div>
        </div>
      )}

      {data.model_3d?.thumbnails && data.model_3d.thumbnails.length > 0 && (
        <div className="gd-section">
          <div className="gd-section-title">
            3D Model Thumbnails
            <span className="gd-section-meta">{data.model_3d.thumbnails.length} views</span>
          </div>
          <div className="gd-frame-grid">
            {data.model_3d.thumbnails.filter((t) => t.image_payload).map((thumb) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={thumb.view}
                src={thumb.image_payload!}
                alt={thumb.view}
                className="gd-frame-thumb gd-zoomable"
                title={thumb.view}
                onClick={() => onZoom(thumb.image_payload!)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Agent placeholder tabs ────────────────────────────────────────────────────

function AgentTab({ label, data }: { label: string; data: unknown }) {
  if (!data) {
    return (
      <div className="gd-tab-empty">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" style={{ opacity: 0.3 }}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 3" />
        </svg>
        <p>{label} output not yet available for this run.</p>
      </div>
    );
  }
  return (
    <div className="gd-tab-body">
      <pre className="gd-json-pre">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

// ── Modal shell ───────────────────────────────────────────────────────────────

export function GenerationDetailModal({ run, onClose, onDeleted }: { run: RunSummary; onClose: () => void; onDeleted: () => void }) {
  const [activeTab, setActiveTab] = useState<Tab>("inputs");
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const meta = run as unknown as Record<string, unknown>;
  const agentStates = (meta.agent_states ?? {}) as Record<string, unknown>;

  async function handleDelete() {
    setDeleting(true);
    await fetch(`${API_URL}/api/runs/${run.run_id}`, { method: "DELETE" });
    onDeleted();
  }

  return (
    <>
    <div className="gd-overlay" onClick={onClose}>
      <div className="gd-modal" onClick={(e) => e.stopPropagation()}>
        <div className="gd-modal-header">
          <div>
            <h2 className="heading-2" style={{ margin: 0 }}>{run.generation_name}</h2>
            <span className="caption" style={{ color: "var(--muted-fg)", fontFamily: "monospace" }}>
              {run.run_id}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            {confirmDelete ? (
              <>
                <span className="caption" style={{ color: "var(--destructive)" }}>Delete this run?</span>
                <button className="btn btn-destructive btn-sm" onClick={handleDelete} disabled={deleting}>
                  {deleting ? "Deleting…" : "Yes, delete"}
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => setConfirmDelete(false)} disabled={deleting}>
                  Cancel
                </button>
              </>
            ) : (
              <button className="btn btn-ghost btn-sm gd-delete-btn" onClick={() => setConfirmDelete(true)} aria-label="Delete run">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
                </svg>
                Delete
              </button>
            )}
            <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close">
              <XIcon />
            </button>
          </div>
        </div>

        <div className="gd-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`gd-tab${activeTab === tab.id ? " gd-tab-active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="gd-modal-body">
          {activeTab === "inputs"   && <InputsTab run={run} onZoom={setLightboxSrc} />}
          {activeTab === "processed" && <ProcessedTab runId={run.run_id} onZoom={setLightboxSrc} />}
          {activeTab === "vision"   && <AgentTab label="Vision agent" data={agentStates.product_profile} />}
          {activeTab === "summary"  && <AgentTab label="Summary agent" data={agentStates.summary_card} />}
          {activeTab === "imagegen" && <AgentTab label="Image generation" data={(meta.image_iterations as unknown[])?.length ? meta.image_iterations : null} />}
        </div>
      </div>

    </div>

    {lightboxSrc && <Lightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />}
    </>
  );
}
