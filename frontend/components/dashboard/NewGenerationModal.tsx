"use client";

import { useEffect, useRef, useState } from "react";
import { useSSE } from "@/lib/sse";
import { submitRun, type SubmitPayload } from "@/lib/submit";
import { Dropzone, type AssetStatus } from "./Dropzone";
import { Lightbox } from "./Lightbox";
import { ImageIcon, VideoIcon, CubeIcon, XIcon, CheckIcon, PlusIcon } from "./icons";

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

export function NewGenerationModal({ onClose }: { onClose: () => void }) {
  // Required
  const [generationName, setGenerationName] = useState("");
  const [productImageToken, setProductImageToken] = useState<string | null>(null);
  const [descProduct, setDescProduct] = useState("");
  const [descAudience, setDescAudience] = useState("");
  const [descColors, setDescColors] = useState("");

  // Optional media
  const [videoToken, setVideoToken] = useState<string | null>(null);
  const [model3dToken, setModel3dToken] = useState<string | null>(null);
  const [referenceToken, setReferenceToken] = useState<string | null>(null);

  // Steering — all optional; empty means "let the model decide"
  const [aspectRatio, setAspectRatio] = useState("");
  const [cameraPerspective, setCameraPerspective] = useState("");
  const [lightingPreset, setLightingPreset] = useState("");
  const [negativePrompts, setNegativePrompts] = useState("");

  // Mode + conditional
  const [pipelineMode, setPipelineMode] = useState("ecommerce");
  const [ecommerceCount, setEcommerceCount] = useState(5);
  const [socialResearch, setSocialResearch] = useState(false);
  const [abDirections, setAbDirections] = useState("");
  const [seasonalTheme, setSeasonalTheme] = useState<string | null>(null);

  // Supervision
  const [supervisionResearch, setSupervisionResearch] = useState(true);
  const [supervisionImageGen, setSupervisionImageGen] = useState(true);

  // Per-asset processing status (drives submit-time gating & the result screen)
  const [assetStatuses, setAssetStatuses] = useState<Record<string, AssetStatus>>({});
  const setAssetStatus = (key: string) => (s: AssetStatus) =>
    setAssetStatuses((prev) => ({ ...prev, [key]: s }));

  // Submission / streaming
  const [runId, setRunId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // When every submitted asset was already processed on upload, the run reuses
  // those results and finishes instantly — skip dwelling on a processing screen.
  const [optimisticDone, setOptimisticDone] = useState(false);
  const { messages } = useSSE(runId);

  // Enlarged preview (lightbox)
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
      // close the lightbox first if it's open, otherwise the modal
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
    // If all submitted assets are already processed, the run will reuse the
    // cached results and complete near-instantly — show success right away.
    const submitted: [string, string | null][] = [
      ["product_image", productImageToken],
      ["video", videoToken],
      ["model_3d", model3dToken],
      ["reference_image", referenceToken],
    ];
    setOptimisticDone(
      submitted.every(([key, token]) => !token || assetStatuses[key] === "ready"),
    );
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
      setRunId(id);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Submission failed");
    } finally {
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

  // Translate the raw SSE stream into a friendly result — never shown as logs.
  const FAIL_LABEL: Record<string, string> = {
    pipeline_error: "Product image",
    video_failed: "Product video",
    model_failed: "3D model",
    reference_failed: "Reference image",
  };
  const DONE_LABEL: Record<string, string> = {
    text_processed: "Product copy",
    image_processed: "Product image",
    reference_processed: "Reference image",
    video_processed: "Product video",
    model_processed: "3D model",
  };
  const failures = [...new Set(messages.filter((m) => FAIL_LABEL[m.event]).map((m) => FAIL_LABEL[m.event]))];
  const processedList = [...new Set(messages.filter((m) => DONE_LABEL[m.event]).map((m) => DONE_LABEL[m.event]))];
  const errored = messages.some((m) => m.event === "pipeline_error");
  const completed = messages.some((m) => m.event === "pipeline_complete");
  const ended = messages.some((m) => m.event === "stream_end");
  const terminal = errored || completed || ended || optimisticDone;
  const phase: "processing" | "success" | "partial" | "failed" = !terminal
    ? "processing"
    : errored
      ? "failed"
      : failures.length > 0
        ? "partial"
        : "success";

  return (
   <>
    <div className="modal-overlay open" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="genTitle">
        <div className="modal-head">
          <div>
            <h2 className="heading-2" id="genTitle">{runId ? (generationName || "New Generation") : "New Generation"}</h2>
            <p>
              {runId
                ? "Your generation is on its way through the pipeline."
                : "Give Pixpilot a product and creative direction — it renders a batch through the full pipeline."}
            </p>
          </div>
          <button className="modal-close" aria-label="Close" onClick={onClose}><XIcon /></button>
        </div>

        {runId ? (
          <>
            <div className="modal-body">
              {phase === "processing" && (
                <div className="gen-result">
                  <div className="spinner" />
                  <div className="res-title">Processing…</div>
                  <div className="res-sub">Pixpilot is preparing your generation. This only takes a moment.</div>
                </div>
              )}
              {phase === "success" && (
                <div className="gen-result">
                  <div className="res-icon ok"><CheckIcon /></div>
                  <div className="res-title">Generation ready</div>
                  <div className="res-sub">All assets were processed successfully.</div>
                  {processedList.length > 0 && (
                    <ul className="res-assets">
                      {processedList.map((l) => (
                        <li key={l}><CheckIcon className="ck" /> {l}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              {phase === "partial" && (
                <div className="gen-result">
                  <div className="res-icon bad"><XIcon strokeWidth={2.4} /></div>
                  <div className="res-title">Some assets couldn’t be processed</div>
                  <div className="res-sub">Your generation continued without them.</div>
                  <ul className="res-assets">
                    {failures.map((l) => (
                      <li key={l} className="bad"><XIcon strokeWidth={2.4} /> {l} failed to process</li>
                    ))}
                  </ul>
                </div>
              )}
              {phase === "failed" && (
                <div className="gen-result">
                  <div className="res-icon bad"><XIcon strokeWidth={2.4} /></div>
                  <div className="res-title">Generation couldn’t start</div>
                  <div className="res-sub">The product image failed to process. Please try a different file.</div>
                </div>
              )}
            </div>
            <div className="modal-foot">
              <span className="gen-hint">
                {phase === "processing" ? "Working…" : phase === "success" ? "Done" : "Finished with issues"}
              </span>
              <button type="button" className="btn btn-cta" onClick={onClose}>Done</button>
            </div>
          </>
        ) : (
          <>
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
          </>
        )}
      </div>
    </div>
    {zoom && <Lightbox src={zoom} onClose={() => setZoom(null)} />}
   </>
  );
}
