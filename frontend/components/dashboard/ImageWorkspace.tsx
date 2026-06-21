"use client";

import { useState } from "react";
import { CheckIcon } from "./icons";

interface Props {
  runId: string;
  initialImageUrl: string;
  initialIteration: number;
  initialPrompt: string;
  initialSeed: number | null;
}

type Status = "idle" | "submitting" | "error";

export function ImageWorkspace({
  runId,
  initialImageUrl,
  initialIteration,
}: Props) {
  const [imageSrc, setImageSrc] = useState(initialImageUrl);
  const [iteration, setIteration] = useState(initialIteration);
  const [feedback, setFeedback] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [approved, setApproved] = useState(false);

  const maxReached = iteration >= 10;

  async function handleRevise() {
    if (!feedback.trim() || status === "submitting") return;
    setStatus("submitting");
    setErrorMsg("");

    try {
      const resp = await fetch(`/api/runs/${runId}/revise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback: feedback.trim(), iteration }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Unknown error" }));
        if (resp.status === 400 && err.detail === "max_iterations_reached") {
          setIteration(10);
          setStatus("idle");
          return;
        }
        throw new Error(err.detail ?? `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setImageSrc(data.image_url);
      setIteration(data.iteration);
      setFeedback("");
      setStatus("idle");
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Revision failed. Please try again."
      );
      setStatus("error");
    }
  }

  async function handleApprove() {
    try {
      const resp = await fetch(imageSrc);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pixpilot_v${iteration}.png`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Download failed — image still visible, user can right-click save
    }
    setApproved(true);
  }

  return (
    <div className="image-workspace">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className="image-workspace-preview"
        src={imageSrc}
        alt={`Generated product image iteration ${iteration}`}
      />

      <div className="image-workspace-meta">
        <span>Iteration {iteration} of 10</span>
      </div>

      {approved ? (
        <div className="image-workspace-done">
          <CheckIcon style={{ width: 16, height: 16 }} />
          Image downloaded — run complete.
        </div>
      ) : maxReached ? (
        <p className="image-workspace-max">
          Maximum revisions reached — approve the image above or start a new run.
        </p>
      ) : (
        <div className="image-workspace-form">
          <label className="image-workspace-label">What would you like to change?</label>
          <textarea
            className="image-workspace-input"
            placeholder="e.g. Make the background darker and add golden rim lighting"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            disabled={status === "submitting"}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void handleRevise();
            }}
          />
          {status === "error" && (
            <div className="image-workspace-error">{errorMsg}</div>
          )}
          <div className="image-workspace-actions">
            <button
              className="btn btn-outline btn-sm"
              onClick={() => void handleRevise()}
              disabled={status === "submitting" || !feedback.trim()}
            >
              {status === "submitting" ? (
                <><span className="btn-spin" /> Generating…</>
              ) : (
                "Submit Revision"
              )}
            </button>
            <button
              className="btn btn-default btn-sm"
              onClick={() => void handleApprove()}
              disabled={status === "submitting"}
            >
              Approve &amp; Download
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
