"use client";

import { useEffect, useState, useCallback } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SettingsData {
  openai_api_key: string;
  anthropic_api_key: string;
  google_api_key: string;
  fal_api_key: string;
  serpapi_api_key: string;
  openai_vision_model: string;
  anthropic_vision_model: string;
  google_vision_model: string;
  summary_model: string;
  prompt_model: string;
  vision_priority: string;
}

type VisionProvider = "openai" | "anthropic" | "google";

const PROVIDER_DISPLAY: Record<VisionProvider, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
};

// --- Sortable Item ---

interface SortableItemProps {
  id: string;
  index: number;
  label: string;
}

function SortableItem({ id, index, label }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "12px 16px",
    background: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    marginBottom: 8,
    userSelect: "none",
    cursor: isDragging ? "grabbing" : "grab",
    zIndex: isDragging ? 10 : undefined,
    position: "relative",
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {/* Drag handle */}
      <span
        style={{
          color: "var(--muted-fg)",
          fontSize: 18,
          lineHeight: 1,
          cursor: "grab",
          flexShrink: 0,
        }}
        aria-hidden="true"
      >
        ⠿
      </span>

      {/* Provider name */}
      <span style={{ flex: 1, fontWeight: 500, fontSize: 14, color: "var(--fg)" }}>
        {label}
      </span>

      {/* Position badge */}
      <span
        style={{
          width: 22,
          height: 22,
          borderRadius: "50%",
          background: "var(--primary)",
          color: "var(--surface)",
          fontSize: 11,
          fontWeight: 700,
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
        }}
      >
        {index + 1}
      </span>
    </div>
  );
}

// --- API Key row dirty-state tracking ---

interface KeyState {
  value: string;
  dirty: boolean;
  saved: boolean;
}

function makeKeyState(value: string): KeyState {
  return { value, dirty: false, saved: false };
}

// --- Main Component ---

export function ModelsPage() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // API Keys
  const [keys, setKeys] = useState<Record<string, KeyState>>({
    openai_api_key: makeKeyState(""),
    anthropic_api_key: makeKeyState(""),
    google_api_key: makeKeyState(""),
    fal_api_key: makeKeyState(""),
    serpapi_api_key: makeKeyState(""),
  });

  // Models
  const [models, setModels] = useState<Record<string, string>>({
    openai_vision_model: "",
    anthropic_vision_model: "",
    google_vision_model: "",
    summary_model: "",
    prompt_model: "",
  });

  // Vision priority order
  const [visionOrder, setVisionOrder] = useState<VisionProvider[]>([
    "openai",
    "anthropic",
    "google",
  ]);

  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Fetch settings on mount
  useEffect(() => {
    fetch(`${API_URL}/api/settings`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<SettingsData>;
      })
      .then((data) => {
        setKeys({
          openai_api_key: makeKeyState(data.openai_api_key ?? ""),
          anthropic_api_key: makeKeyState(data.anthropic_api_key ?? ""),
          google_api_key: makeKeyState(data.google_api_key ?? ""),
          fal_api_key: makeKeyState(data.fal_api_key ?? ""),
          serpapi_api_key: makeKeyState(data.serpapi_api_key ?? ""),
        });
        setModels({
          openai_vision_model: data.openai_vision_model ?? "",
          anthropic_vision_model: data.anthropic_vision_model ?? "",
          google_vision_model: data.google_vision_model ?? "",
          summary_model: data.summary_model ?? "",
          prompt_model: data.prompt_model ?? "",
        });

        if (data.vision_priority) {
          const parsed = data.vision_priority
            .split(",")
            .map((s) => s.trim())
            .filter((s): s is VisionProvider =>
              ["openai", "anthropic", "google"].includes(s)
            );
          if (parsed.length === 3) {
            setVisionOrder(parsed);
          }
        }

        setLoading(false);
      })
      .catch((err) => {
        setLoadError(`Failed to load settings: ${err.message}`);
        setLoading(false);
      });
  }, []);

  const handleKeyChange = useCallback(
    (field: string, value: string) => {
      setKeys((prev) => ({
        ...prev,
        [field]: { value, dirty: true, saved: false },
      }));
    },
    []
  );

  const handleModelChange = useCallback((field: string, value: string) => {
    setModels((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setVisionOrder((prev) => {
      const oldIndex = prev.indexOf(active.id as VisionProvider);
      const newIndex = prev.indexOf(over.id as VisionProvider);
      return arrayMove(prev, oldIndex, newIndex);
    });
  }, []);

  const handleSave = useCallback(async () => {
    setSaveStatus("saving");

    const body: Partial<SettingsData> = {};

    // Only include dirty keys or non-empty model values
    for (const [field, state] of Object.entries(keys)) {
      if (state.dirty && state.value !== "") {
        (body as Record<string, string>)[field] = state.value;
      }
    }

    for (const [field, value] of Object.entries(models)) {
      if (value !== "") {
        (body as Record<string, string>)[field] = value;
      }
    }

    body.vision_priority = visionOrder.join(",");

    try {
      const r = await fetch(`${API_URL}/api/settings`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);

      // Mark dirty keys as saved
      setKeys((prev) => {
        const next = { ...prev };
        for (const field of Object.keys(next)) {
          if (next[field].dirty) {
            next[field] = { ...next[field], dirty: false, saved: true };
          }
        }
        return next;
      });

      setSaveStatus("saved");

      // Reset to idle after 3s
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch {
      setSaveStatus("error");
    }
  }, [keys, models, visionOrder]);

  // --- Render ---

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

  const keyProviders: Array<{
    label: string;
    field: string;
    placeholder: string;
  }> = [
    { label: "OpenAI", field: "openai_api_key", placeholder: "sk-…" },
    { label: "Anthropic", field: "anthropic_api_key", placeholder: "sk-ant-…" },
    { label: "Google", field: "google_api_key", placeholder: "AIza…" },
    { label: "Fal", field: "fal_api_key", placeholder: "fal-…" },
    { label: "SerpAPI", field: "serpapi_api_key", placeholder: "API key…" },
  ];

  const modelFields: Array<{
    label: string;
    field: string;
    placeholder: string;
  }> = [
    { label: "OpenAI Vision Model", field: "openai_vision_model", placeholder: "e.g. gpt-4o" },
    {
      label: "Anthropic Vision Model",
      field: "anthropic_vision_model",
      placeholder: "e.g. claude-3-5-sonnet-20241022",
    },
    {
      label: "Google Vision Model",
      field: "google_vision_model",
      placeholder: "e.g. gemini-2.0-flash",
    },
    {
      label: "Summary Model",
      field: "summary_model",
      placeholder: "e.g. claude-haiku-4-5-20251001",
    },
    { label: "Prompt Model", field: "prompt_model", placeholder: "e.g. claude-sonnet-4-6" },
  ];

  return (
    <div className="gen-page">
      {/* Page header */}
      <div className="gen-page-header">
        <h1 className="heading-2">Models &amp; API Keys</h1>
      </div>

      {/* Card grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 20,
        }}
      >
        {/* Section A — API Keys */}
        <div className="card" style={{ padding: "20px 24px" }}>
          <h2 className="heading-3" style={{ marginBottom: 16 }}>
            API Keys
          </h2>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {keyProviders.map(({ label, field, placeholder }) => {
              const state = keys[field];
              return (
                <div key={field}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 6,
                    }}
                  >
                    <span className="overline">{label}</span>
                    {/* Saved indicator dot */}
                    <span
                      title={state.saved ? "Saved" : "Unsaved"}
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: state.saved ? "var(--green)" : "var(--border)",
                        display: "inline-block",
                        transition: "background 0.3s",
                      }}
                    />
                  </div>
                  <input
                    type="password"
                    className="finput"
                    placeholder={placeholder}
                    value={state.value}
                    onChange={(e) => handleKeyChange(field, e.target.value)}
                    autoComplete="off"
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* Section B — Models */}
        <div className="card" style={{ padding: "20px 24px" }}>
          <h2 className="heading-3" style={{ marginBottom: 16 }}>
            Model Names
          </h2>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {modelFields.map(({ label, field, placeholder }) => (
              <div key={field}>
                <div style={{ marginBottom: 6 }}>
                  <span className="caption" style={{ color: "var(--fg)", fontWeight: 500 }}>
                    {label}
                  </span>
                </div>
                <input
                  type="text"
                  className="finput"
                  placeholder={placeholder}
                  value={models[field]}
                  onChange={(e) => handleModelChange(field, e.target.value)}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Section C — Vision Priority (full width) */}
        <div className="card" style={{ padding: "20px 24px", gridColumn: "1 / -1" }}>
          <h2 className="heading-3" style={{ marginBottom: 6 }}>
            Vision Priority
          </h2>
          <p className="caption" style={{ marginBottom: 16 }}>
            Drag to reorder which provider is tried first for vision tasks.
          </p>

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={visionOrder}
              strategy={verticalListSortingStrategy}
            >
              {visionOrder.map((id, index) => (
                <SortableItem
                  key={id}
                  id={id}
                  index={index}
                  label={PROVIDER_DISPLAY[id]}
                />
              ))}
            </SortableContext>
          </DndContext>
        </div>
      </div>

      {/* Save button */}
      <div style={{ marginTop: 24 }}>
        <button
          className="btn btn-default"
          onClick={handleSave}
          disabled={saveStatus === "saving"}
          style={{ width: "100%" }}
        >
          {saveStatus === "saving" ? "Saving…" : "Save Settings"}
        </button>

        {saveStatus === "saved" && (
          <p className="caption" style={{ marginTop: 8, color: "var(--green)", textAlign: "center" }}>
            Settings saved.
          </p>
        )}
        {saveStatus === "error" && (
          <p className="caption" style={{ marginTop: 8, color: "var(--destructive)", textAlign: "center" }}>
            Failed to save settings. Please try again.
          </p>
        )}
      </div>
    </div>
  );
}
