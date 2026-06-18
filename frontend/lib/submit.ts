// frontend/lib/submit.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SteeringParams {
  aspect_ratio: string;
  camera_perspective: string;
  lighting_preset: string;
  negative_prompts: string;
}

export interface SupervisionSettings {
  research: boolean;
  image_gen: boolean;
}

export interface SubmitPayload {
  description_product: string;
  description_audience: string;
  description_colors: string;
  product_image_token: string;
  video_token: string | null;
  model_3d_token: string | null;
  reference_image_token: string | null;
  steering: SteeringParams;
  pipeline_mode: string;
  ecommerce_image_count: number;
  social_research_enabled: boolean;
  ab_concept_directions: string;
  seasonal_theme: string | null;
  supervision: SupervisionSettings;
}

export async function submitRun(payload: SubmitPayload): Promise<string> {
  const res = await fetch(`${API_URL}/api/runs/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Submit failed: ${res.status}`);
  }
  const { run_id } = await res.json();
  return run_id as string;
}
