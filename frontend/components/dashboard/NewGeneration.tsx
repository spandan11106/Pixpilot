"use client";

import { useState } from "react";
import { PlusIcon } from "./icons";
import { NewGenerationModal } from "./NewGenerationModal";

export function NewGeneration() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-cta" onClick={() => setOpen(true)}>
        <PlusIcon /> New Generation
      </button>
      {open && <NewGenerationModal onClose={() => setOpen(false)} />}
    </>
  );
}
