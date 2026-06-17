// frontend/app/page.tsx
"use client";

import { useState, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { useSSE } from "@/lib/sse";
import { uploadFile } from "@/lib/upload";
import { submitRun, SubmitPayload } from "@/lib/submit";

type UploadState = { token: string | null; status: "idle" | "uploading" | "ready" | "error"; error?: string };

function useFileUpload(fileType: string) {
  const [state, setState] = useState<UploadState>({ token: null, status: "idle" });

  async function handleFile(file: File) {
    setState({ token: null, status: "uploading" });
    try {
      const token = await uploadFile(file, fileType);
      setState({ token, status: "ready" });
    } catch (e) {
      setState({ token: null, status: "error", error: e instanceof Error ? e.message : "Upload failed" });
    }
  }

  function clear() {
    setState({ token: null, status: "idle" });
  }

  return { state, handleFile, clear };
}

function FileField({ label, fileType, accept, onToken }: {
  label: string; fileType: string; accept: string; onToken?: (token: string | null) => void;
}) {
  const { state, handleFile, clear } = useFileUpload(fileType);

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    handleFile(file).then(() => onToken?.(state.token));
  }

  // notify parent when token changes
  const prev = useRef<string | null>(null);
  if (prev.current !== state.token) {
    prev.current = state.token;
    onToken?.(state.token);
  }

  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Input type="file" accept={accept} onChange={onChange} />
      {state.status === "uploading" && <p className="text-xs text-muted-foreground">uploading…</p>}
      {state.status === "ready" && <p className="text-xs text-green-600">ready</p>}
      {state.status === "error" && <p className="text-xs text-destructive">{state.error}</p>}
    </div>
  );
}

export default function Home() {
  const [runId, setRunId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { messages, connected } = useSSE(runId);

  // Required
  const [productImageToken, setProductImageToken] = useState<string | null>(null);
  const [descProduct, setDescProduct] = useState("");
  const [descAudience, setDescAudience] = useState("");
  const [descColors, setDescColors] = useState("");

  // Optional media tokens
  const [videoToken, setVideoToken] = useState<string | null>(null);
  const [model3dToken, setModel3dToken] = useState<string | null>(null);
  const [referenceToken, setReferenceToken] = useState<string | null>(null);
  const [logoToken, setLogoToken] = useState<string | null>(null);
  const [logoPlacement, setLogoPlacement] = useState("bottom-left");

  // Steering
  const [aspectRatio, setAspectRatio] = useState("1:1");
  const [cameraPerspective, setCameraPerspective] = useState("Studio Eye-Level");
  const [lightingPreset, setLightingPreset] = useState("Studio Softlight");
  const [negativePrompts, setNegativePrompts] = useState("");

  // Mode
  const [pipelineMode, setPipelineMode] = useState("ecommerce");
  const [ecommerceCount, setEcommerceCount] = useState(5);
  const [socialResearch, setSocialResearch] = useState(false);
  const [abDirections, setAbDirections] = useState("");
  const [seasonalTheme, setSeasonalTheme] = useState<string | null>(null);

  // Supervision
  const [supervisionResearch, setSupervisionResearch] = useState(true);
  const [supervisionImageGen, setSupervisionImageGen] = useState(true);

  const canSubmit = !!productImageToken && descProduct.trim() && descAudience.trim() && descColors.trim();

  async function handleSubmit() {
    if (!productImageToken) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload: SubmitPayload = {
        description_product: descProduct.trim(),
        description_audience: descAudience.trim(),
        description_colors: descColors.trim(),
        product_image_token: productImageToken,
        video_token: videoToken,
        model_3d_token: model3dToken,
        reference_image_token: referenceToken,
        logo_token: logoToken,
        logo_placement: logoPlacement,
        steering: {
          aspect_ratio: aspectRatio,
          camera_perspective: cameraPerspective,
          lighting_preset: lightingPreset,
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

  return (
    <main className="min-h-screen bg-background p-8">
      <div className="mx-auto max-w-3xl space-y-8">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">Pixpilot</h1>
          <p className="text-muted-foreground text-lg">AI-assisted product image generation pipeline</p>
        </div>

        <Separator />

        {!runId && (
          <Card>
            <CardHeader><CardTitle>New Run</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <Accordion multiple defaultValue={["required"]}>

                {/* Section 1 — Required */}
                <AccordionItem value="required">
                  <AccordionTrigger>Required Inputs</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-2">
                    <FileField
                      label="Product Image (jpg/png/webp)"
                      fileType="product_image"
                      accept=".jpg,.jpeg,.png,.webp"
                      onToken={setProductImageToken}
                    />
                    <div className="space-y-1">
                      <Label>Product Info</Label>
                      <Textarea
                        placeholder="Key features, name, USPs…"
                        value={descProduct}
                        onChange={e => setDescProduct(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label>Target Audience</Label>
                      <Textarea
                        placeholder="Who this product is for…"
                        value={descAudience}
                        onChange={e => setDescAudience(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label>Desired Colors</Label>
                      <Textarea
                        placeholder="Color palette preferences…"
                        value={descColors}
                        onChange={e => setDescColors(e.target.value)}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                {/* Section 2 — Optional Media */}
                <AccordionItem value="media">
                  <AccordionTrigger>Optional Media</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-2">
                    <FileField label="Product Video (mp4/mov/webm, max 100MB)" fileType="video" accept=".mp4,.mov,.webm" onToken={setVideoToken} />
                    <FileField label="3D Model (gltf/obj/usdz, max 50MB)" fileType="model_3d" accept=".gltf,.obj,.usdz" onToken={setModel3dToken} />
                    <FileField label="Reference Image (jpg/png/webp)" fileType="reference_image" accept=".jpg,.jpeg,.png,.webp" onToken={setReferenceToken} />
                    <FileField label="Company Logo (svg/png/jpeg)" fileType="logo" accept=".svg,.png,.jpg,.jpeg" onToken={setLogoToken} />
                    {logoToken && (
                      <div className="space-y-1">
                        <Label>Logo Placement</Label>
                        <Select value={logoPlacement} onValueChange={v => { if (v !== null) setLogoPlacement(v); }}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="top-left">Top Left</SelectItem>
                            <SelectItem value="top-right">Top Right</SelectItem>
                            <SelectItem value="bottom-left">Bottom Left (default)</SelectItem>
                            <SelectItem value="bottom-right">Bottom Right</SelectItem>
                            <SelectItem value="center-watermark">Center Watermark</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </AccordionContent>
                </AccordionItem>

                {/* Section 3 — Visual Steering */}
                <AccordionItem value="steering">
                  <AccordionTrigger>Visual Steering</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-2">
                    <div className="space-y-1">
                      <Label>Aspect Ratio</Label>
                      <Select value={aspectRatio} onValueChange={v => { if (v !== null) setAspectRatio(v); }}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1:1">1:1 Square</SelectItem>
                          <SelectItem value="9:16">9:16 Vertical</SelectItem>
                          <SelectItem value="16:9">16:9 Landscape</SelectItem>
                          <SelectItem value="4:5">4:5 Portrait</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Camera Perspective</Label>
                      <Select value={cameraPerspective} onValueChange={v => { if (v !== null) setCameraPerspective(v); }}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Studio Eye-Level">Studio Eye-Level</SelectItem>
                          <SelectItem value="Flat Lay (Top-Down)">Flat Lay (Top-Down)</SelectItem>
                          <SelectItem value="Close-Up Macro">Close-Up Macro</SelectItem>
                          <SelectItem value="Dynamic 3/4 View">Dynamic 3/4 View</SelectItem>
                          <SelectItem value="Hero Shot (Low Angle)">Hero Shot (Low Angle)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Lighting / Vibe Preset</Label>
                      <Select value={lightingPreset} onValueChange={v => { if (v !== null) setLightingPreset(v); }}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Studio Softlight">Studio Softlight</SelectItem>
                          <SelectItem value="Natural Sunshine">Natural Sunshine</SelectItem>
                          <SelectItem value="Golden Hour Warmth">Golden Hour Warmth</SelectItem>
                          <SelectItem value="Moody / Chiaroscuro">Moody / Chiaroscuro</SelectItem>
                          <SelectItem value="Neon / Cyberpunk">Neon / Cyberpunk</SelectItem>
                          <SelectItem value="Minimalist Pastel">Minimalist Pastel</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label>Negative Prompts</Label>
                      <Textarea
                        placeholder="Elements to exclude…"
                        value={negativePrompts}
                        onChange={e => setNegativePrompts(e.target.value)}
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                {/* Section 4 — Pipeline Mode */}
                <AccordionItem value="mode">
                  <AccordionTrigger>Pipeline Mode</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-2">
                    <div className="space-y-1">
                      <Label>Mode</Label>
                      <Select value={pipelineMode} onValueChange={v => { if (v !== null) setPipelineMode(v); }}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ecommerce">E-Commerce Batch</SelectItem>
                          <SelectItem value="social">Social Media Marketing</SelectItem>
                          <SelectItem value="ab">A/B Concept Exploration</SelectItem>
                          <SelectItem value="seasonal">Seasonal / Holiday Campaign</SelectItem>
                          <SelectItem value="summarize">Summarization & Research Opt-In</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    {pipelineMode === "ecommerce" && (
                      <div className="space-y-1">
                        <Label>Number of Images (5–12)</Label>
                        <Input
                          type="number"
                          min={5}
                          max={12}
                          value={ecommerceCount}
                          onChange={e => setEcommerceCount(Number(e.target.value))}
                        />
                      </div>
                    )}
                    {pipelineMode === "social" && (
                      <div className="flex items-center gap-2">
                        <Switch checked={socialResearch} onCheckedChange={setSocialResearch} />
                        <Label>Enable Market Research</Label>
                      </div>
                    )}
                    {pipelineMode === "ab" && (
                      <div className="space-y-1">
                        <Label>Concept Directions (optional)</Label>
                        <Textarea
                          placeholder="Leave blank for agent to choose…"
                          value={abDirections}
                          onChange={e => setAbDirections(e.target.value)}
                        />
                      </div>
                    )}
                    {pipelineMode === "seasonal" && (
                      <div className="space-y-1">
                        <Label>Seasonal Theme</Label>
                        <Select value={seasonalTheme ?? ""} onValueChange={v => setSeasonalTheme(v || null)}>
                          <SelectTrigger><SelectValue placeholder="Select theme…" /></SelectTrigger>
                          <SelectContent>
                            {["Christmas","Halloween","Summer","Spring","Diwali","Black Friday","Valentine's Day","Eid","Hanukkah","New Year"].map(t => (
                              <SelectItem key={t} value={t}>{t}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </AccordionContent>
                </AccordionItem>

                {/* Section 5 — Supervision */}
                <AccordionItem value="supervision">
                  <AccordionTrigger>Supervision</AccordionTrigger>
                  <AccordionContent className="space-y-3 pt-2">
                    <div className="flex items-center gap-2">
                      <Switch checked={supervisionResearch} onCheckedChange={setSupervisionResearch} />
                      <Label>Research supervision</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch checked={supervisionImageGen} onCheckedChange={setSupervisionImageGen} />
                      <Label>Image generation supervision</Label>
                    </div>
                    <p className="text-xs text-muted-foreground">Final Review Deck is always shown.</p>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>

              <Button onClick={handleSubmit} disabled={!canSubmit || submitting}>
                {submitting ? "Submitting…" : "Run Pipeline"}
              </Button>
              {submitError && <p className="text-destructive text-sm">{submitError}</p>}
            </CardContent>
          </Card>
        )}

        {runId && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Pipeline Events</CardTitle>
                <Badge variant={connected ? "default" : "secondary"}>
                  {connected ? "Connected" : "Done"}
                </Badge>
              </div>
              <p className="font-mono text-xs text-muted-foreground">{runId}</p>
            </CardHeader>
            <CardContent>
              <div className="bg-muted rounded-md p-4 space-y-2 max-h-80 overflow-y-auto font-mono text-sm">
                {messages.length === 0 && <p className="text-muted-foreground">Waiting for events…</p>}
                {messages.map((msg, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="text-primary font-semibold">[{msg.event}]</span>
                    <span className="text-muted-foreground break-all">{JSON.stringify(msg.data)}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
