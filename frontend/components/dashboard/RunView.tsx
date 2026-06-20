"use client";

import { useEffect, useRef } from "react";
import { useSSE } from "@/lib/sse";
import { StageTracker, type Stage } from "./StageTracker";
import { type RunMeta } from "./NewGenerationModal";
import { CheckIcon, XIcon } from "./icons";

const PIPELINE_STAGES: { key: string; name: string; label: string }[] = [
  { key: "process_text",      name: "Text",     label: "1" },
  { key: "process_image",     name: "Image",    label: "2" },
  { key: "process_video",     name: "Media",    label: "3" },
  { key: "process_model",     name: "3D Model", label: "4" },
  { key: "finalize",          name: "Finalize", label: "5" },
  { key: "pipeline_complete", name: "Done",     label: "6" },
];

const MODE_LABELS: Record<string, string> = {
  ecommerce: "E-Commerce Batch",
  social:    "Social Media",
  ab:        "A/B Exploration",
  seasonal:  "Seasonal Campaign",
  summarize: "Summarization",
};

function deriveStages(seenEvents: Set<string>): Stage[] {
  let foundActive = false;
  return PIPELINE_STAGES.map((s, i) => {
    if (seenEvents.has(s.key)) return { name: s.name, meta: "done", state: "done" as const };
    const prevDone = i === 0 || seenEvents.has(PIPELINE_STAGES[i - 1].key);
    if (!foundActive && prevDone) {
      foundActive = true;
      return { name: s.name, meta: "in progress", state: "active" as const, label: s.label };
    }
    return { name: s.name, meta: "pending", state: "pending" as const, label: s.label };
  });
}

export function RunView({ run, onDismiss }: { run: RunMeta; onDismiss: () => void }) {
  const { messages } = useSSE(run.runId);
  const logRef = useRef<HTMLDivElement>(null);

  const seenEvents = new Set(messages.map((m) => m.event));
  const stages = deriveStages(seenEvents);

  const isComplete = seenEvents.has("pipeline_complete");
  const hasError   = seenEvents.has("pipeline_error");
  const isTerminal = isComplete || hasError || seenEvents.has("stream_end");

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="run-view">
      <div className="run-head">
        <div>
          <h1 className="heading-2">{run.name}</h1>
          <span className="badge badge-outline" style={{ marginTop: 4, display: "inline-flex" }}>
            {MODE_LABELS[run.mode] ?? run.mode}
          </span>
        </div>
        {isTerminal && (
          <button className="btn btn-ghost" onClick={onDismiss}>
            <XIcon /> Dismiss
          </button>
        )}
      </div>

      <div className="card run-stage-card">
        <div className="run-stage-head">
          {isComplete && (
            <span className="badge badge-success"><span className="pulse" /><CheckIcon style={{ width: 12, height: 12 }} /> Complete</span>
          )}
          {hasError && (
            <span className="badge badge-error"><XIcon style={{ width: 12, height: 12 }} /> Failed</span>
          )}
          {!isTerminal && (
            <span className="badge badge-amber"><span className="pulse" /> Running</span>
          )}
        </div>
        <StageTracker stages={stages} bare />
      </div>

      <div className="run-body">
        {/* Left: inputs panel */}
        <div className="run-inputs card">
          <div className="run-inputs-head">Inputs</div>
          {run.imagePreviewUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img className="run-product-img" src={run.imagePreviewUrl} alt="Product" />
          ) : (
            <div className="run-product-placeholder">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
            </div>
          )}
          <div className="run-inputs-meta">
            <div className="run-input-row">
              <span className="overline">Generation</span>
              <span className="body-s" style={{ fontWeight: 500 }}>{run.name}</span>
            </div>
            <div className="run-input-row">
              <span className="overline">Mode</span>
              <span className="body-s">{MODE_LABELS[run.mode] ?? run.mode}</span>
            </div>
            <div className="run-input-row">
              <span className="overline">Run ID</span>
              <span className="caption" style={{ fontFamily: "monospace", wordBreak: "break-all" }}>{run.runId}</span>
            </div>
          </div>
        </div>

        {/* Right: live SSE log */}
        <div className="run-log card">
          <div className="run-log-head">Live Events</div>
          <div className="run-log-body" ref={logRef}>
            {messages.length === 0 && (
              <div className="run-log-empty">
                <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                Waiting for pipeline events…
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`log-item ${msg.event.includes("error") || msg.event.includes("failed") ? "log-error" : msg.event === "pipeline_complete" ? "log-ok" : ""}`}>
                <span className="log-event">{msg.event}</span>
                {Object.keys(msg.data).length > 0 && (
                  <span className="log-data">
                    {Object.entries(msg.data)
                      .filter(([k]) => k !== "run_id")
                      .slice(0, 3)
                      .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
                      .join(" · ")}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
