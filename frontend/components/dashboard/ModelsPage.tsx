"use client";

import { useEffect, useState, useCallback } from "react";
import { SectionHead } from "./models/SectionHead";
import { ProviderCard } from "./models/ProviderCard";
import { TaskModelTable, type TaskProvider, type TaskProviderDef } from "./models/TaskModelTable";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SettingsData {
  openai_api_key: string;
  anthropic_api_key: string;
  google_api_key: string;
  fal_api_key: string;
  // Vision Analysis
  openai_vision_model: string;
  anthropic_vision_model: string;
  google_vision_model: string;
  vision_priority: string;
  // Summary
  openai_summary_model: string;
  anthropic_summary_model: string;
  google_summary_model: string;
  summary_priority: string;
  // Image Prompt
  openai_prompt_model: string;
  anthropic_prompt_model: string;
  google_prompt_model: string;
  prompt_priority: string;
  // Image Generation
  fal_image_model: string;
  openai_image_model: string;
  image_gen_priority: string;
}

interface KeyState {
  value: string;
  dirty: boolean;
}

function makeKey(value: string): KeyState {
  return { value, dirty: false };
}

const ALL_PROVIDERS: Array<{
  id: string;
  name: string;
  role: string;
  initials: string;
  bg: string;
  color: string;
  keyField: string;
}> = [
  {
    id: "openai",
    name: "OpenAI",
    role: "GPT vision & reasoning",
    initials: "OA",
    bg: "rgba(var(--green-rgb),0.18)",
    color: "var(--green)",
    keyField: "openai_api_key",
  },
  {
    id: "anthropic",
    name: "Anthropic",
    role: "Claude vision & text",
    initials: "AN",
    bg: "rgba(var(--accent2-rgb),0.2)",
    color: "var(--accent-2)",
    keyField: "anthropic_api_key",
  },
  {
    id: "google",
    name: "Google",
    role: "Gemini multimodal",
    initials: "GG",
    bg: "rgba(var(--primary-rgb),0.18)",
    color: "var(--primary)",
    keyField: "google_api_key",
  },
  {
    id: "fal",
    name: "Fal",
    role: "Image generation via FLUX",
    initials: "FL",
    bg: "rgba(var(--secondary-rgb),0.18)",
    color: "var(--secondary)",
    keyField: "fal_api_key",
  },
];

const VISION_PROVIDERS: TaskProviderDef[] = [
  { id: "openai",    name: "OpenAI",    initials: "OA", bg: "rgba(var(--green-rgb),0.18)",    color: "var(--green)",     modelField: "openai_vision_model",    placeholder: "e.g. gpt-4o" },
  { id: "anthropic", name: "Anthropic", initials: "AN", bg: "rgba(var(--accent2-rgb),0.2)",   color: "var(--accent-2)",  modelField: "anthropic_vision_model", placeholder: "e.g. claude-sonnet-4-6" },
  { id: "google",    name: "Google",    initials: "GG", bg: "rgba(var(--primary-rgb),0.18)",  color: "var(--primary)",   modelField: "google_vision_model",    placeholder: "e.g. gemini-2.0-flash" },
];

const SUMMARY_PROVIDERS: TaskProviderDef[] = [
  { id: "openai",    name: "OpenAI",    initials: "OA", bg: "rgba(var(--green-rgb),0.18)",    color: "var(--green)",     modelField: "openai_summary_model",    placeholder: "e.g. gpt-4o-mini" },
  { id: "anthropic", name: "Anthropic", initials: "AN", bg: "rgba(var(--accent2-rgb),0.2)",   color: "var(--accent-2)",  modelField: "anthropic_summary_model", placeholder: "e.g. claude-haiku-4-5-20251001" },
  { id: "google",    name: "Google",    initials: "GG", bg: "rgba(var(--primary-rgb),0.18)",  color: "var(--primary)",   modelField: "google_summary_model",    placeholder: "e.g. gemini-2.0-flash" },
];

const PROMPT_PROVIDERS: TaskProviderDef[] = [
  { id: "openai",    name: "OpenAI",    initials: "OA", bg: "rgba(var(--green-rgb),0.18)",    color: "var(--green)",     modelField: "openai_prompt_model",    placeholder: "e.g. gpt-4o" },
  { id: "anthropic", name: "Anthropic", initials: "AN", bg: "rgba(var(--accent2-rgb),0.2)",   color: "var(--accent-2)",  modelField: "anthropic_prompt_model", placeholder: "e.g. claude-sonnet-4-6" },
  { id: "google",    name: "Google",    initials: "GG", bg: "rgba(var(--primary-rgb),0.18)",  color: "var(--primary)",   modelField: "google_prompt_model",    placeholder: "e.g. gemini-2.0-flash" },
];

const DEFAULT_ORDER: TaskProvider[] = ["openai", "anthropic", "google"];
const DEFAULT_IMAGE_GEN_ORDER: TaskProvider[] = ["fal", "openai"];

const IMAGE_GEN_PROVIDERS: TaskProviderDef[] = [
  { id: "fal",    name: "fal.ai",  initials: "FL", bg: "rgba(var(--secondary-rgb),0.18)", color: "var(--secondary)", modelField: "fal_image_model",    placeholder: "e.g. fal-ai/flux/dev/image-to-image" },
  { id: "openai", name: "OpenAI",  initials: "OA", bg: "rgba(var(--green-rgb),0.18)",    color: "var(--green)",     modelField: "openai_image_model",  placeholder: "e.g. dall-e-3" },
];

function parseOrder(raw: string, valid: string[], expectedLen: number): TaskProvider[] | null {
  const parsed = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => valid.includes(s));
  return parsed.length === expectedLen ? parsed : null;
}

export function ModelsPage() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [keys, setKeys] = useState<Record<string, KeyState>>({
    openai_api_key: makeKey(""),
    anthropic_api_key: makeKey(""),
    google_api_key: makeKey(""),
    fal_api_key: makeKey(""),
  });

  const [models, setModels] = useState<Record<string, string>>({
    openai_vision_model: "",
    anthropic_vision_model: "",
    google_vision_model: "",
    openai_summary_model: "",
    anthropic_summary_model: "",
    google_summary_model: "",
    openai_prompt_model: "",
    anthropic_prompt_model: "",
    google_prompt_model: "",
    fal_image_model: "",
    openai_image_model: "",
  });

  const [visionOrder,   setVisionOrder]   = useState<TaskProvider[]>([...DEFAULT_ORDER]);
  const [summaryOrder,  setSummaryOrder]  = useState<TaskProvider[]>([...DEFAULT_ORDER]);
  const [promptOrder,   setPromptOrder]   = useState<TaskProvider[]>([...DEFAULT_ORDER]);
  const [imageGenOrder, setImageGenOrder] = useState<TaskProvider[]>([...DEFAULT_IMAGE_GEN_ORDER]);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  useEffect(() => {
    fetch(`${API_URL}/api/settings`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<SettingsData>;
      })
      .then((data) => {
        setKeys({
          openai_api_key: makeKey(data.openai_api_key ?? ""),
          anthropic_api_key: makeKey(data.anthropic_api_key ?? ""),
          google_api_key: makeKey(data.google_api_key ?? ""),
          fal_api_key: makeKey(data.fal_api_key ?? ""),
        });
        setModels({
          openai_vision_model:    data.openai_vision_model    ?? "",
          anthropic_vision_model: data.anthropic_vision_model ?? "",
          google_vision_model:    data.google_vision_model    ?? "",
          openai_summary_model:    data.openai_summary_model    ?? "",
          anthropic_summary_model: data.anthropic_summary_model ?? "",
          google_summary_model:    data.google_summary_model    ?? "",
          openai_prompt_model:    data.openai_prompt_model    ?? "",
          anthropic_prompt_model: data.anthropic_prompt_model ?? "",
          google_prompt_model:    data.google_prompt_model    ?? "",
          fal_image_model:   data.fal_image_model   ?? "",
          openai_image_model: data.openai_image_model ?? "",
        });
        const v3 = ["openai", "anthropic", "google"];
        const v2 = ["fal", "openai"];
        if (data.vision_priority)    setVisionOrder(parseOrder(data.vision_priority, v3, 3)       ?? DEFAULT_ORDER);
        if (data.summary_priority)   setSummaryOrder(parseOrder(data.summary_priority, v3, 3)     ?? DEFAULT_ORDER);
        if (data.prompt_priority)    setPromptOrder(parseOrder(data.prompt_priority, v3, 3)       ?? DEFAULT_ORDER);
        if (data.image_gen_priority) setImageGenOrder(parseOrder(data.image_gen_priority, v2, 2)  ?? DEFAULT_IMAGE_GEN_ORDER);
        setLoading(false);
      })
      .catch((err) => {
        setLoadError(`Failed to load settings: ${err.message}`);
        setLoading(false);
      });
  }, []);

  const handleKeyChange = useCallback((field: string, value: string) => {
    setKeys((prev) => ({ ...prev, [field]: { value, dirty: true } }));
  }, []);

  const handleModelChange = useCallback((field: string, value: string) => {
    setModels((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleDiscard = useCallback(() => {
    setKeys((prev) => {
      const next = { ...prev };
      for (const k of Object.keys(next)) next[k] = { ...next[k], dirty: false };
      return next;
    });
    setSaveStatus("idle");
  }, []);

  const handleSave = useCallback(async () => {
    setSaveStatus("saving");
    const body: Partial<Record<string, string>> = {};

    for (const [field, state] of Object.entries(keys)) {
      if (state.dirty && state.value !== "") body[field] = state.value;
    }
    for (const [field, value] of Object.entries(models)) {
      if (value !== "") body[field] = value;
    }
    body.vision_priority    = visionOrder.join(",");
    body.summary_priority   = summaryOrder.join(",");
    body.prompt_priority    = promptOrder.join(",");
    body.image_gen_priority = imageGenOrder.join(",");

    try {
      const r = await fetch(`${API_URL}/api/settings`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);

      setKeys((prev) => {
        const next = { ...prev };
        for (const k of Object.keys(next)) next[k] = { ...next[k], dirty: false };
        return next;
      });
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
    }
  }, [keys, models, visionOrder, summaryOrder, promptOrder, imageGenOrder]);

  if (loading) {
    return (
      <div className="gen-page-empty">
        <span className="spinner" style={{ width: 24, height: 24, borderWidth: 2 }} />
        Loading settings…
      </div>
    );
  }

  if (loadError) {
    return <div className="gen-page-empty gen-page-error">{loadError}</div>;
  }

  const hasDirty = Object.values(keys).some((k) => k.dirty);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", flex: 1 }}>
      {/* Page header */}
      <div className="page-head">
        <div>
          <h1 className="display-l">Models &amp; API Keys</h1>
          <p>
            Connect your AI providers, pin the model for each pipeline task, and set the
            fallback order Pixpilot uses when a provider fails or is rate-limited.
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-3)" }}>
          <button
            className="btn btn-ghost"
            onClick={handleDiscard}
            disabled={!hasDirty || saveStatus === "saving"}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            Discard
          </button>
          <button
            className="btn btn-cta"
            onClick={handleSave}
            disabled={saveStatus === "saving"}
          >
            {saveStatus === "saving" ? (
              <>
                <span className="btn-spin" />
                Saving…
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                  <polyline points="17 21 17 13 7 13 7 21" />
                  <polyline points="7 3 7 8 15 8" />
                </svg>
                {saveStatus === "saved" ? "Saved!" : "Save changes"}
              </>
            )}
          </button>
        </div>
      </div>

      {saveStatus === "error" && (
        <p className="caption" style={{ color: "var(--destructive)" }}>
          Save failed — please check your connection and try again.
        </p>
      )}

      {/* API keys */}
      <section>
        <SectionHead
          overline="API keys"
          heading="Connected providers"
          hint="Add a key to activate a provider."
        />
        <div className="prov-grid">
          {ALL_PROVIDERS.map((p) => (
            <ProviderCard
              key={p.id}
              providerId={p.id}
              name={p.name}
              role={p.role}
              initials={p.initials}
              badgeBg={p.bg}
              badgeColor={p.color}
              keyValue={keys[p.keyField]?.value ?? ""}
              onKeyChange={(v) => handleKeyChange(p.keyField, v)}
            />
          ))}
        </div>
      </section>

      {/* Vision Analysis */}
      <section>
        <SectionHead
          overline="Vision analysis"
          heading="Product vision model"
          hint="Analyzes product image, reference, 3D renders, and video frames into a structured profile."
        />
        <TaskModelTable
          providers={VISION_PROVIDERS}
          order={visionOrder}
          models={models}
          onOrderChange={setVisionOrder}
          onModelChange={handleModelChange}
        />
      </section>

      {/* Summary */}
      <section>
        <SectionHead
          overline="Summarizer"
          heading="Summary model"
          hint="Merges the vision profile with user descriptions into the Input Summary Card."
        />
        <TaskModelTable
          providers={SUMMARY_PROVIDERS}
          order={summaryOrder}
          models={models}
          onOrderChange={setSummaryOrder}
          onModelChange={handleModelChange}
        />
      </section>

      {/* Image Prompt */}
      <section>
        <SectionHead
          overline="Image prompt"
          heading="Prompt refinement model"
          hint="Translates natural language feedback into revised FLUX generation prompts."
        />
        <TaskModelTable
          providers={PROMPT_PROVIDERS}
          order={promptOrder}
          models={models}
          onOrderChange={setPromptOrder}
          onModelChange={handleModelChange}
        />
      </section>

      {/* Image Generation */}
      <section>
        <SectionHead
          overline="Image generation"
          heading="Generation model"
          hint="Pin the model for each provider and drag to set which one Pixpilot tries first."
        />
        <TaskModelTable
          providers={IMAGE_GEN_PROVIDERS}
          order={imageGenOrder}
          models={models}
          onOrderChange={setImageGenOrder}
          onModelChange={handleModelChange}
        />
      </section>
    </div>
  );
}
