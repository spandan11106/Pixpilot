"use client";
import { CheckIcon } from "./icons";

export type Stage = {
  name: string;
  meta: string;
  state: "done" | "active" | "pending";
  label?: string;
};

export function StageTracker({ stages, bare }: { stages: Stage[]; bare?: boolean }) {
  return (
    <div className="stages" style={bare ? { padding: 0 } : undefined}>
      {stages.map((stage) => (
        <div key={stage.name} className={`stage ${stage.state === "pending" ? "" : stage.state}`}>
          <div className="stage-dot">
            {stage.state === "done" ? <CheckIcon /> : stage.label}
          </div>
          <span className="stage-name">{stage.name}</span>
          <span className="stage-meta">{stage.meta}</span>
        </div>
      ))}
    </div>
  );
}
