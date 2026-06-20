# Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the complex mocked dashboard (KPIs, charts, queue, activity) with a focused two-state page: empty state when no run is active, and a full run view (inputs panel + stage tracker + live SSE log) when a run is in progress or has just completed.

**Architecture:** `Dashboard` holds `modalOpen: boolean` and `activeRun: RunMeta | null`. When the modal submits successfully it calls `onRunStart(runId, meta)` and immediately closes. Dashboard switches to `RunView` which subscribes to the SSE stream independently. `EmptyState` is shown when `activeRun` is null.

**Tech Stack:** Next.js / React 18, TypeScript, CSS Modules (dashboard.css scoped under `.pp-dash`), native `EventSource` via `useSSE` hook

## Global Constraints

- All CSS must be scoped under `.pp-dash` to avoid leaking into the shadcn theme
- No new npm packages
- `NewGenerationModal` receives `onRunStart` and `onClose`; it must not hold SSE state after this change
- `StageTracker` stays as-is; only its `Stage` type import source changes

---

### Task 1: Delete dead components and mock data

**Files:**
- Delete: `frontend/components/dashboard/KpiGrid.tsx`
- Delete: `frontend/components/dashboard/Charts.tsx`
- Delete: `frontend/components/dashboard/ActiveJob.tsx`
- Delete: `frontend/components/dashboard/RecentGenerations.tsx`
- Delete: `frontend/components/dashboard/RenderQueue.tsx`
- Delete: `frontend/components/dashboard/ActivityFeed.tsx`
- Delete: `frontend/components/dashboard/data.ts`
- Modify: `frontend/components/dashboard/StageTracker.tsx`

**Interfaces:**
- Produces: `Stage` type defined locally in `StageTracker.tsx`

- [ ] **Step 1: Move Stage type into StageTracker**

`StageTracker.tsx` currently imports `Stage` from `./data`. Replace the import with an inline definition:

```tsx
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
```

- [ ] **Step 2: Delete the seven dead files**

```bash
cd frontend
rm components/dashboard/KpiGrid.tsx \
   components/dashboard/Charts.tsx \
   components/dashboard/ActiveJob.tsx \
   components/dashboard/RecentGenerations.tsx \
   components/dashboard/RenderQueue.tsx \
   components/dashboard/ActivityFeed.tsx \
   components/dashboard/data.ts
```

- [ ] **Step 3: Verify TypeScript still compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors related to the deleted files. (Dashboard.tsx will have errors because it still imports the deleted components — that is fixed in Task 3.)

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(dashboard): delete mocked KPI, chart, queue, and activity components"
```

---

### Task 2: Add `onImageUrl` callback to Dropzone

**Files:**
- Modify: `frontend/components/dashboard/Dropzone.tsx`

**Interfaces:**
- Produces: `DropzoneProps.onImageUrl?: (url: string) => void` — called in `buildPreview` immediately after the object URL is created (image preview kind only)

- [ ] **Step 1: Add `onImageUrl` to `DropzoneProps` and call it in `buildPreview`**

In `Dropzone.tsx`, add `onImageUrl?: (url: string) => void` to the `DropzoneProps` type and to the function signature, then call it inside `buildPreview`:

```tsx
export type DropzoneProps = {
  fileType: string;
  accept: string;
  title: string;
  sub: string;
  preview: PreviewKind;
  icon: "image" | "video" | "cube";
  maxMB?: number;
  required?: boolean;
  promptIcon?: ReactNode;
  onToken: (token: string | null) => void;
  onStatus?: (status: AssetStatus) => void;
  onZoom?: (src: string) => void;
  onImageUrl?: (url: string) => void;   // NEW
};

export function Dropzone({
  fileType, accept, title, sub, preview, icon, maxMB, required, promptIcon,
  onToken, onStatus, onZoom, onImageUrl,   // NEW
}: DropzoneProps) {
  // ... existing state ...

  function buildPreview(f: File) {
    if (preview === "image") {
      revoke();
      const url = URL.createObjectURL(f);
      objUrlRef.current = url;
      setImgUrl(url);
      onImageUrl?.(url);   // NEW
    }
  }

  // rest of file unchanged
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/dashboard/Dropzone.tsx
git commit -m "feat(dropzone): expose onImageUrl callback for product image preview"
```

---

### Task 3: Lift modal and run state into Dashboard; refactor modal to remove SSE

**Files:**
- Modify: `frontend/components/dashboard/Dashboard.tsx`
- Modify: `frontend/components/dashboard/NewGeneration.tsx`
- Modify: `frontend/components/dashboard/Topbar.tsx`
- Modify: `frontend/components/dashboard/NewGenerationModal.tsx`

**Interfaces:**
- Consumes: `Stage` from `./StageTracker` (Task 1)
- Produces:
  - `RunMeta` interface: `{ runId: string; name: string; imagePreviewUrl: string | null; mode: string }`
  - `NewGenerationModal` props: `{ onClose: () => void; onRunStart: (meta: RunMeta) => void }`
  - `NewGeneration` props: `{ onClick: () => void }`
  - `Topbar` props: `{ onNewGeneration: () => void }`
  - `Dashboard` state: `modalOpen: boolean`, `activeRun: RunMeta | null`

- [ ] **Step 1: Refactor `NewGeneration.tsx` to be a pure button**

```tsx
"use client";
import { PlusIcon } from "./icons";

export function NewGeneration({ onClick }: { onClick: () => void }) {
  return (
    <button className="btn btn-cta" onClick={onClick}>
      <PlusIcon /> New Generation
    </button>
  );
}
```

- [ ] **Step 2: Refactor `Topbar.tsx` to accept `onNewGeneration` prop**

```tsx
import { SearchIcon, BellIcon, DownloadIcon } from "./icons";
import { NewGeneration } from "./NewGeneration";
import { ThemeToggle } from "./ThemeToggle";

export function Topbar({ onNewGeneration }: { onNewGeneration: () => void }) {
  return (
    <header className="topbar">
      <div className="search">
        <SearchIcon />
        <input type="text" placeholder="Search prompts, jobs, models…" />
      </div>
      <div className="topbar-actions">
        <ThemeToggle />
        <button className="icon-btn" aria-label="Notifications">
          <BellIcon />
          <span className="dot" />
        </button>
        <button className="btn btn-outline btn-sm"><DownloadIcon /> Export</button>
        <NewGeneration onClick={onNewGeneration} />
      </div>
    </header>
  );
}
```

- [ ] **Step 3: Add `RunMeta` interface and update `NewGenerationModal`**

The modal no longer manages SSE or shows a result screen. When the HTTP submit succeeds it calls `onRunStart` with the run ID and captured metadata, then `onClose`. Remove: `runId` state, `useSSE`, `optimisticDone`, `phase`, the post-submit JSX branch, the 5-second auto-close effect.

Add `imagePreviewUrl` state (set via `onImageUrl` on the product image Dropzone).

Key prop change: old `onClose: () => void` stays. New: `onRunStart: (meta: RunMeta) => void`.

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { submitRun, type SubmitPayload } from "@/lib/submit";
import { Dropzone, type AssetStatus } from "./Dropzone";
import { Lightbox } from "./Lightbox";
import { ImageIcon, VideoIcon, CubeIcon, XIcon, CheckIcon, PlusIcon } from "./icons";

export interface RunMeta {
  runId: string;
  name: string;
  imagePreviewUrl: string | null;
  mode: string;
}

const ASPECT_RATIOS = [
  { value: "1:1", w: 14, h: 14 },
  { value: "9:16", w: 10, h: 16 },
  { value: "16:9", w: 18, h: 10 },
  { value: "4:5", w: 12, h: 15 },
];

const CAMERAS = [
  "Studio Eye-Level", "Flat Lay (Top-Down)", "Close-Up Macro",
  "Dynamic 3/4 View", "Hero Shot (Low Angle)",
];

const LIGHTING = [
  { name: "Studio Softlight", swatch: "linear-gradient(135deg,#ffffff,#e2ddd2)" },
  { name: "Natural Sunshine", swatch: "linear-gradient(135deg,#FFE594,#FFC24A)" },
  { name: "Golden Hour Warmth", swatch: "linear-gradient(135deg,#FFAF38,#D9662A)" },
  { name: "Moody / Chiaroscuro", swatch: "linear-gradient(135deg,#454a63,#10121d)" },
  { name: "Neon / Cyberpunk", swatch: "linear-gradient(135deg,#303ED2,#B026D3)" },
  { name: "Minimalist Pastel", swatch: "linear-gradient(135deg,#FFF7EB,#C9DBFF)" },
];

const MODES = [
  { value: "ecommerce", title: "E-Commerce Batch", sub: "High-volume, catalog-ready product renders" },
  { value: "social", title: "Social Media Marketing", sub: "Platform-optimized creatives and crops" },
  { value: "ab", title: "A/B Concept Exploration", sub: "Multiple distinct concepts to compare" },
  { value: "seasonal", title: "Seasonal / Holiday Campaign", sub: "Themed assets for a seasonal push" },
  { value: "summarize", title: "Summarization & Research Opt-In", sub: "Share results to help improve models" },
];

const SEASONS = [
  "Christmas", "Halloween", "Summer", "Spring", "Diwali",
  "Black Friday", "Valentine's Day", "Eid", "Hanukkah", "New Year",
];

function Toggle({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button type="button" role="switch" aria-checked={on} className={`toggle ${on ? "on" : ""}`} onClick={onClick} />
  );
}

export function NewGenerationModal({
  onClose,
  onRunStart,
}: {
  onClose: () => void;
  onRunStart: (meta: RunMeta) => void;
}) {
  const [generationName, setGenerationName] = useState("");
  const [productImageToken, setProductImageToken] = useState<string | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [descProduct, setDescProduct] = useState("");
  const [descAudience, setDescAudience] = useState("");
  const [descColors, setDescColors] = useState("");

  const [videoToken, setVideoToken] = useState<string | null>(null);
  const [model3dToken, setModel3dToken] = useState<string | null>(null);
  const [referenceToken, setReferenceToken] = useState<string | null>(null);

  const [aspectRatio, setAspectRatio] = useState("");
  const [cameraPerspective, setCameraPerspective] = useState("");
  const [lightingPreset, setLightingPreset] = useState("");
  const [negativePrompts, setNegativePrompts] = useState("");

  const [pipelineMode, setPipelineMode] = useState("ecommerce");
  const [ecommerceCount, setEcommerceCount] = useState(5);
  const [socialResearch, setSocialResearch] = useState(false);
  const [abDirections, setAbDirections] = useState("");
  const [seasonalTheme, setSeasonalTheme] = useState<string | null>(null);

  const [supervisionResearch, setSupervisionResearch] = useState(true);
  const [supervisionImageGen, setSupervisionImageGen] = useState(true);

  const [assetStatuses, setAssetStatuses] = useState<Record<string, AssetStatus>>({});
  const setAssetStatus = (key: string) => (s: AssetStatus) =>
    setAssetStatuses((prev) => ({ ...prev, [key]: s }));

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [zoom, setZoom] = useState<string | null>(null);
  const zoomRef = useRef<string | null>(null);
  useEffect(() => { zoomRef.current = zoom; }, [zoom]);

  const canSubmit =
    !!generationName.trim() && !!productImageToken &&
    !!descProduct.trim() && !!descAudience.trim() && !!descColors.trim();

  useEffect(() => {
    document.body.style.overflow = "hidden";
    function onKey(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      if (zoomRef.current) setZoom(null);
      else onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  async function handleSubmit() {
    if (!productImageToken || !canSubmit) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload: SubmitPayload = {
        generation_name: generationName.trim(),
        description_product: descProduct.trim(),
        description_audience: descAudience.trim(),
        description_colors: descColors.trim(),
        product_image_token: productImageToken,
        video_token: videoToken,
        model_3d_token: model3dToken,
        reference_image_token: referenceToken,
        steering: {
          aspect_ratio: aspectRatio || null,
          camera_perspective: cameraPerspective || null,
          lighting_preset: lightingPreset || null,
          negative_prompts: negativePrompts,
        },
        pipeline_mode: pipelineMode,
        ecommerce_image_count: ecommerceCount,
        social_research_enabled: socialResearch,
        ab_concept_directions: abDirections,
        seasonal_theme: pipelineMode === "seasonal" ? seasonalTheme : null,
        supervision: { research: supervisionResearch, image_gen: supervisionImageGen },
      };
      const id = await submitRun(payload);
      onRunStart({ runId: id, name: generationName.trim(), imagePreviewUrl, mode: pipelineMode });
      onClose();
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Submission failed");
      setSubmitting(false);
    }
  }

  const hint = submitError
    ? submitError
    : submitting
      ? "Submitting…"
      : canSubmit
        ? "Ready to generate"
        : "Product image + all required fields needed";

  return (
   <>
    <div className="modal-overlay open" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="genTitle">
        <div className="modal-head">
          <div>
            <h2 className="heading-2" id="genTitle">New Generation</h2>
            <p>Give Pixpilot a product and creative direction — it renders a batch through the full pipeline.</p>
          </div>
          <button className="modal-close" aria-label="Close" onClick={onClose}><XIcon /></button>
        </div>

        <div className="modal-body">
          {/* 1. Required Inputs */}
          <section className="form-section">
            <div className="section-title"><span className="section-num">1</span><h3 className="heading-3">Required Inputs</h3></div>

            <div className="field">
              <span className="field-label">Generation Name <span className="req">*</span></span>
              <input
                className="finput"
                placeholder="e.g. Summer Sneaker Launch"
                value={generationName}
                onChange={(e) => setGenerationName(e.target.value)}
              />
              <span className="field-hint">Shown in the dashboard. The run is stored under a separate generated ID.</span>
            </div>

            <div className="field">
              <span className="field-label">Product Image <span className="req">*</span></span>
              <Dropzone
                fileType="product_image"
                accept=".jpg,.jpeg,.png,.webp"
                title="Drop product image or click to browse"
                sub="JPG · JPEG · PNG · WEBP"
                preview="image"
                icon="image"
                required
                onToken={setProductImageToken}
                onStatus={setAssetStatus("product_image")}
                onZoom={setZoom}
                onImageUrl={setImagePreviewUrl}
              />
            </div>

            <div className="field">
              <span className="field-label">Product Info <span className="req">*</span></span>
              <textarea className="ftextarea" placeholder="Product name, key features, unique selling points…"
                value={descProduct} onChange={(e) => setDescProduct(e.target.value)} />
            </div>

            <div className="grid-2">
              <div className="field">
                <span className="field-label">Target Audience <span className="req">*</span></span>
                <textarea className="ftextarea" placeholder="Who is this for? Demographics, mindset, context…"
                  value={descAudience} onChange={(e) => setDescAudience(e.target.value)} />
              </div>
              <div className="field">
                <span className="field-label">Desired Colors <span className="req">*</span></span>
                <textarea className="ftextarea" placeholder="Palette preferences, brand colors, mood…"
                  value={descColors} onChange={(e) => setDescColors(e.target.value)} />
              </div>
            </div>
          </section>

          {/* 2. Optional Media */}
          <section className="form-section">
            <div className="section-title"><span className="section-num">2</span><h3 className="heading-3">Optional Media</h3><span className="opt">Optional</span></div>
            <div className="grid-3">
              <div className="field">
                <span className="field-label">Product Video</span>
                <Dropzone fileType="video" accept=".mp4,.mov,.webm" title="Product Video" sub="MP4 · MOV · WEBM · ≤100MB"
                  preview="frames" icon="video" maxMB={100} promptIcon={<VideoIcon />} onToken={setVideoToken}
                  onStatus={setAssetStatus("video")} onZoom={setZoom} />
              </div>
              <div className="field">
                <span className="field-label">3D Model</span>
                <Dropzone fileType="model_3d" accept=".gltf,.obj,.usdz" title="3D Model" sub="GLTF · OBJ · USDZ · ≤50MB"
                  preview="views" icon="cube" maxMB={50} promptIcon={<CubeIcon />} onToken={setModel3dToken}
                  onStatus={setAssetStatus("model_3d")} onZoom={setZoom} />
              </div>
              <div className="field">
                <span className="field-label">Reference Image</span>
                <Dropzone fileType="reference_image" accept=".jpg,.jpeg,.png,.webp" title="Reference Image" sub="JPG · PNG · WEBP"
                  preview="image" icon="image" promptIcon={<ImageIcon strokeWidth={1.8} />} onToken={setReferenceToken}
                  onStatus={setAssetStatus("reference_image")} onZoom={setZoom} />
              </div>
            </div>
          </section>

          {/* 3. Visual Steering */}
          <section className="form-section">
            <div className="section-title"><span className="section-num">3</span><h3 className="heading-3">Visual Steering</h3><span className="opt">Optional</span></div>
            <span className="field-hint">Tap a selection again to clear it. Anything you leave unset, the image generation model decides for you.</span>

            <div className="field">
              <span className="field-label">Aspect Ratio</span>
              <div className="seg">
                {ASPECT_RATIOS.map((ar) => (
                  <button type="button" key={ar.value} className={aspectRatio === ar.value ? "selected" : ""}
                    onClick={() => setAspectRatio((v) => (v === ar.value ? "" : ar.value))}>
                    <span className="ar-box" style={{ width: ar.w, height: ar.h }} />{ar.value}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <span className="field-label">Camera Perspective</span>
              <div className="chip-grid">
                {CAMERAS.map((c) => (
                  <button type="button" key={c} className={`chip ${cameraPerspective === c ? "selected" : ""}`}
                    onClick={() => setCameraPerspective((v) => (v === c ? "" : c))}>
                    {c}<CheckIcon className="ck" />
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <span className="field-label">Lighting / Vibe Preset</span>
              <div className="chip-grid">
                {LIGHTING.map((l) => (
                  <button type="button" key={l.name} className={`chip ${lightingPreset === l.name ? "selected" : ""}`}
                    onClick={() => setLightingPreset((v) => (v === l.name ? "" : l.name))}>
                    <span className="swatch" style={{ background: l.swatch }} />{l.name}<CheckIcon className="ck" />
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <span className="field-label">Negative Prompts</span>
              <textarea className="ftextarea" placeholder="Elements to exclude — e.g. text, watermark, extra fingers, clutter…"
                value={negativePrompts} onChange={(e) => setNegativePrompts(e.target.value)} />
            </div>
          </section>

          {/* 4. Pipeline Mode */}
          <section className="form-section">
            <div className="section-title"><span className="section-num">4</span><h3 className="heading-3">Pipeline Mode</h3></div>
            <div className="mode-grid">
              {MODES.map((m) => (
                <button type="button" key={m.value} className={`mode ${pipelineMode === m.value ? "selected" : ""}`}
                  onClick={() => setPipelineMode(m.value)}>
                  <span className="radio" />
                  <div><div className="m-title">{m.title}</div><div className="m-sub">{m.sub}</div></div>
                </button>
              ))}
            </div>

            {pipelineMode === "ecommerce" && (
              <div className="field">
                <span className="field-label">Number of Images (5–12)</span>
                <input className="finput" type="number" min={5} max={12} value={ecommerceCount}
                  onChange={(e) => setEcommerceCount(Number(e.target.value))} />
              </div>
            )}
            {pipelineMode === "social" && (
              <div className="toggle-row">
                <Toggle on={socialResearch} onClick={() => setSocialResearch((v) => !v)} />
                <span className="field-label">Enable Market Research</span>
              </div>
            )}
            {pipelineMode === "ab" && (
              <div className="field">
                <span className="field-label">Concept Directions (optional)</span>
                <textarea className="ftextarea" placeholder="Leave blank for the agent to choose…"
                  value={abDirections} onChange={(e) => setAbDirections(e.target.value)} />
              </div>
            )}
            {pipelineMode === "seasonal" && (
              <div className="field">
                <span className="field-label">Seasonal Theme</span>
                <div className="chip-grid">
                  {SEASONS.map((s) => (
                    <button type="button" key={s} className={`chip ${seasonalTheme === s ? "selected" : ""}`}
                      onClick={() => setSeasonalTheme(s)}>
                      {s}<CheckIcon className="ck" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* 5. Supervision */}
          <section className="form-section">
            <div className="section-title"><span className="section-num">5</span><h3 className="heading-3">Supervision</h3></div>
            <div className="toggle-row">
              <Toggle on={supervisionResearch} onClick={() => setSupervisionResearch((v) => !v)} />
              <span className="field-label">Research supervision</span>
            </div>
            <div className="toggle-row">
              <Toggle on={supervisionImageGen} onClick={() => setSupervisionImageGen((v) => !v)} />
              <span className="field-label">Image generation supervision</span>
            </div>
            <span className="field-hint">Final Review Deck is always shown.</span>
          </section>
        </div>

        <div className="modal-foot">
          <span className={`gen-hint ${submitError ? "error" : ""}`}>{hint}</span>
          <div style={{ display: "flex", gap: "var(--space-3)" }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="button" className={`btn btn-cta ${!canSubmit || submitting ? "is-disabled" : ""}`}
              disabled={!canSubmit || submitting} onClick={handleSubmit}>
              {submitting ? <><span className="btn-spin" /> Processing…</> : <><PlusIcon /> Create Generation</>}
            </button>
          </div>
        </div>
      </div>
    </div>
    {zoom && <Lightbox src={zoom} onClose={() => setZoom(null)} />}
   </>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/dashboard/NewGeneration.tsx \
        frontend/components/dashboard/Topbar.tsx \
        frontend/components/dashboard/NewGenerationModal.tsx
git commit -m "refactor(modal): lift run state to Dashboard; modal calls onRunStart on submit"
```

---

### Task 4: Create EmptyState component

**Files:**
- Create: `frontend/components/dashboard/EmptyState.tsx`

**Interfaces:**
- Consumes: `onClick: () => void` prop
- Produces: `EmptyState` named export

- [ ] **Step 1: Create the file**

```tsx
import { PlusIcon } from "./icons";

export function EmptyState({ onNewGeneration }: { onNewGeneration: () => void }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
      </div>
      <h2 className="heading-2">No active run</h2>
      <p className="empty-sub">Start a new generation to see the pipeline in action.</p>
      <button className="btn btn-cta" onClick={onNewGeneration}>
        <PlusIcon /> New Generation
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/dashboard/EmptyState.tsx
git commit -m "feat(dashboard): add EmptyState component"
```

---

### Task 5: Create RunView component

**Files:**
- Create: `frontend/components/dashboard/RunView.tsx`

**Interfaces:**
- Consumes:
  - `RunMeta` from `./NewGenerationModal`
  - `useSSE` from `@/lib/sse`
  - `StageTracker`, `Stage` from `./StageTracker`
- Produces: `RunView` named export with props `{ run: RunMeta; onDismiss: () => void }`

Pipeline stages are derived from the SSE event stream. The backend emits events named after LangGraph nodes: `process_text`, `process_image`, `process_video`, `process_model`, `finalize`, `pipeline_complete`. Terminal events: `pipeline_complete`, `pipeline_error`, `stream_end`.

Stage state logic: a stage is "done" if its event has been seen; the first stage not done whose predecessor is done is "active"; the rest are "pending".

- [ ] **Step 1: Create `RunView.tsx`**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/dashboard/RunView.tsx
git commit -m "feat(dashboard): add RunView with stage tracker and live SSE event log"
```

---

### Task 6: Wire everything together in Dashboard

**Files:**
- Modify: `frontend/components/dashboard/Dashboard.tsx`

**Interfaces:**
- Consumes: `EmptyState`, `RunView`, `NewGenerationModal`, `RunMeta` (from `./NewGenerationModal`), `Sidebar`, `Topbar`
- Produces: complete page with modal/empty/run states

- [ ] **Step 1: Rewrite Dashboard.tsx**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/dashboard/Dashboard.tsx
git commit -m "feat(dashboard): wire EmptyState and RunView into Dashboard with lifted run state"
```

---

### Task 7: CSS — add new styles, remove dead styles

**Files:**
- Modify: `frontend/components/dashboard/dashboard.css`

- [ ] **Step 1: Remove dead CSS blocks**

Delete the following rule groups from `dashboard.css` (they correspond to deleted components):
- `.pp-dash .kpi-grid` through `.pp-dash .trend` (KPI row section)
- `.pp-dash .cols` (two-column layout)
- `.pp-dash .gen-grid` through `.pp-dash .t6` (Generations grid + thumb colors)
- `.pp-dash .queue` through `.pp-dash .q-eta` (Queue panel)
- `.pp-dash .activity` through `.pp-dash .act-body` (Activity)
- `.pp-dash .kpi-spark` (KPI sparklines)
- `.pp-dash .charts` through `.pp-dash .chart-x span` (Charts row)
- `.pp-dash .gauge-wrap` through `.pp-dash .gauge-stats` + `@keyframes pp-gauge` (Gauge)
- `.pp-dash .job-body` through `@keyframes pp-scan` (Active job)
- `.pp-dash .countdown` (countdown)
- `.pp-dash .queue-list.collapsed`, `.pp-dash .group-head`, `.pp-dash .q-handle` (Queue drag)
- Responsive overrides that reference removed classes: `.pp-dash .cols`, `.pp-dash .kpi-grid`, `.pp-dash .charts`, `.pp-dash .job-body`, `.pp-dash .gen-grid`

- [ ] **Step 2: Add new CSS for EmptyState and RunView**

Append before the `@media` blocks:

```css
/* ---------- Empty state ---------- */
.pp-dash .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  min-height: 60vh;
  text-align: center;
}
.pp-dash .empty-icon {
  width: 80px; height: 80px;
  border-radius: var(--radius-lg);
  background: rgba(var(--primary-rgb), 0.08);
  color: var(--primary);
  display: grid; place-items: center;
}
.pp-dash .empty-sub { color: var(--muted-fg); font-size: 15px; max-width: 36ch; }

/* ---------- Run view ---------- */
.pp-dash .run-view { display: flex; flex-direction: column; gap: var(--space-5); }
.pp-dash .run-head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap; }

.pp-dash .run-stage-card { padding: var(--space-4) var(--space-5); }
.pp-dash .run-stage-head { margin-bottom: var(--space-4); }

.pp-dash .run-body { display: grid; grid-template-columns: 240px 1fr; gap: var(--space-5); align-items: start; }

.pp-dash .run-inputs { display: flex; flex-direction: column; overflow: hidden; }
.pp-dash .run-inputs-head { font-family: var(--font-display); font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted-fg); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--border); }
.pp-dash .run-product-img { width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }
.pp-dash .run-product-placeholder { aspect-ratio: 1; display: grid; place-items: center; background: rgba(var(--primary-rgb),0.05); color: var(--muted-fg); }
.pp-dash .run-inputs-meta { display: flex; flex-direction: column; gap: 0; }
.pp-dash .run-input-row { display: flex; flex-direction: column; gap: 2px; padding: var(--space-3) var(--space-4); border-top: 1px solid var(--border); }

.pp-dash .run-log { display: flex; flex-direction: column; min-height: 360px; max-height: 560px; }
.pp-dash .run-log-head { font-family: var(--font-display); font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted-fg); padding: var(--space-3) var(--space-5); border-bottom: 1px solid var(--border); flex: none; }
.pp-dash .run-log-body { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0; padding: var(--space-2) 0; }
.pp-dash .run-log-empty { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-5); color: var(--muted-fg); font-size: 13px; }

.pp-dash .log-item { display: flex; flex-direction: column; gap: 2px; padding: 6px var(--space-5); border-bottom: 1px solid var(--border); }
.pp-dash .log-item:last-child { border-bottom: none; }
.pp-dash .log-item.log-error { background: rgba(var(--destructive-rgb),0.04); }
.pp-dash .log-item.log-ok { background: rgba(var(--green-rgb),0.04); }
.pp-dash .log-event { font-family: monospace; font-size: 12px; font-weight: 600; color: var(--primary); }
.pp-dash .log-item.log-error .log-event { color: var(--destructive); }
.pp-dash .log-item.log-ok .log-event { color: var(--green); }
.pp-dash .log-data { font-size: 12px; color: var(--muted-fg); word-break: break-word; }
```

- [ ] **Step 3: Fix responsive overrides**

In the `@media (max-width: 1100px)` block, remove references to deleted classes and replace with:

```css
@media (max-width: 1100px) {
  .pp-dash .run-body { grid-template-columns: 1fr; }
  .pp-dash .stages { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 760px) {
  .pp-dash .app { grid-template-columns: 1fr; }
  .pp-dash .sidebar { display: none; }
  .pp-dash .content, .pp-dash .topbar { padding-left: var(--space-5); padding-right: var(--space-5); }
  .pp-dash .stages { grid-template-columns: 1fr 1fr; gap: var(--space-4); }
  .pp-dash .stage::after { display: none; }
}
@media (max-width: 620px) {
  .pp-dash .grid-2, .pp-dash .grid-3, .pp-dash .chip-grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 4: Verify no TypeScript errors and build is clean**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Start dev server and verify visually**

```bash
cd frontend && npm run dev
```

Check:
1. Main page shows empty state with centered "No active run" + "+ New Generation" button
2. Topbar "+ New Generation" button opens the modal
3. Empty state button also opens the modal  
4. Modal form still works (fill required fields, upload image, submit)
5. After submit: modal closes, main page shows RunView with the generation name, image preview, mode badge, stage tracker, and live event log
6. SSE events appear as log lines and the stage tracker advances
7. After `pipeline_complete` / `stream_end`: "Dismiss" button appears, clicking it returns to empty state
8. Theme toggle still works

- [ ] **Step 6: Commit**

```bash
git add frontend/components/dashboard/dashboard.css
git commit -m "style(dashboard): add RunView/EmptyState CSS, remove dead mocked-component styles"
```
