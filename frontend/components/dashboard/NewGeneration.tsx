"use client";
import { PlusIcon } from "./icons";

export function NewGeneration({ onClick }: { onClick: () => void }) {
  return (
    <button className="btn btn-cta" onClick={onClick}>
      <PlusIcon /> New Generation
    </button>
  );
}
