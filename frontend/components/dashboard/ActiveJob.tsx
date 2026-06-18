"use client";

import { useEffect, useState } from "react";
import { activeJobStages } from "./data";
import { StageTracker } from "./StageTracker";
import { ImageIcon, PauseIcon, BoltIcon } from "./icons";

function useCountdown(start = 6) {
  const [seconds, setSeconds] = useState(start);
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => (s <= 1 ? 9 : s - 1)), 1000);
    return () => clearInterval(id);
  }, []);
  return seconds;
}

export function ActiveJob() {
  const seconds = useCountdown(6);

  return (
    <section className="card">
      <div className="section-head">
        <div>
          <h2 className="heading-2">Active Job · #PX-4821</h2>
          <div className="caption" style={{ marginTop: 2 }}>
            “Cinematic product shot, amber studio light, 85mm” · batch of 4 · SDXL-Turbo
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <span className="badge badge-amber"><span className="pulse" /> Rendering</span>
          <button className="btn btn-outline btn-sm"><PauseIcon /> Pause</button>
          <button className="btn btn-cta btn-sm"><BoltIcon /> Prioritize</button>
        </div>
      </div>
      <div className="job-body">
        <div className="job-preview">
          <div className="job-thumb t4">
            <div className="scan" />
            <ImageIcon stroke="var(--surface)" strokeWidth={1.6} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span className="caption">Input reference</span>
            <span className="caption">1 / 4</span>
          </div>
        </div>
        <div className="job-main">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-4)" }}>
            <div>
              <div className="overline">Est. completion</div>
              <div className="countdown">~{seconds}s remaining</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="overline">Progress</div>
              <div className="kpi-num" style={{ fontSize: 22 }}>80%</div>
            </div>
          </div>
          <StageTracker stages={activeJobStages} bare />
        </div>
      </div>
    </section>
  );
}
