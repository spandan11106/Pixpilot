# Product Requirements Document — Version 0.5 (Beta)
# Open-Source Product Image Generation Pipeline

> **Version:** 0.5 Beta
> **Date:** June 20, 2026
> **Status:** Beta Release — Image Generation Only
> **Scope:** Multimodal ingestion, vision analysis, and image generation with revision loops. Market research agent deferred to v1.0
>
> **PROGRESS SUMMARY (as of June 20, 2026):**
> - **Milestone 0 (Infrastructure):** ✅ COMPLETE
> - **Milestone 1 (Ingestion + Vision + Summarizer):** ✅ MOSTLY COMPLETE (backend wired; Input Summary Card displayed inline in live event log; image generation interface missing)
> - **Milestone 2 (Image Generation + Revision):** ⏳ IN PROGRESS (critical path for v0.5 beta)
> - **Milestone 3 (Final Review Deck + Beta Release):** ⏳ NOT STARTED
> - **v1.0 Future:** Market Research Agent, Copy Generation, and Social Publishing deferred
>
> **Changes from v1.0 (Full Roadmap) to v0.5 Beta:**
> - **v0.5 is a minimal beta release** focusing exclusively on image generation pipeline.
> - **Modes reduced from 5 to 3:** Removed "Summarization & Research Opt-In" and "Social Media Marketing" modes (both require market research agent deferred to v1.0). Keeping: E-Commerce Batch, A/B Concept Exploration, Seasonal Campaign.
> - **Market Research Agent deferred to v1.0.** No web search, no crossroads checkpoints, no 60-second question window in v0.5.
> - **Copy/Caption generation removed from v0.5.** Users export images and write copy manually. Deferred to v1.0.
> - **Summarizer Agent included in v0.5:** Merges product profile with user description fields to create Input Summary Card checkpoint for user review before image generation.
> - **SerpAPI and ChromaDB removed from tech stack.** These are deferred with the Market Research Agent to v1.0.
> - **Supervision simplified:** Summary Review checkpoint (user verifies inputs) + Image Generation checkpoint (user approves/revises/restarts). Market Research checkpoint removed.
> - **Focus:** Core image generation with revision loops, 3 flexible modes, summary verification, and local export. Get it working well before adding research complexity.

---

## Table of Contents

1. [What v0.5 Beta Is](#what-v05-beta-is)
2. [What v0.5 Beta Is Not](#what-v05-beta-is-not)
3. [Problem Statement](#problem-statement)
4. [Product Vision](#product-vision)
5. [Who This Is For](#who-this-is-for)
6. [How Users Run This](#how-users-run-this)
7. [User Flow](#user-flow)
8. [Product Inputs](#product-inputs)
9. [Product Features](#product-features)
10. [Supervision & Control Settings](#supervision--control-settings)
11. [Tech Stack](#tech-stack)
12. [System Architecture](#system-architecture)
13. [Local Storage Structure](#local-storage-structure)
14. [Current Status & Next Steps](#current-status--next-steps)
15. [Milestones & Delivery Plan](#milestones--delivery-plan)
16. [Where to Start](#where-to-start)
17. [Testing Strategy](#testing-strategy)
18. [Risks & Mitigations](#risks--mitigations)
19. [Success Metrics (KPIs)](#success-metrics-kpis)
20. [Open Questions](#open-questions)

---

## What v0.5 Beta Is

Version 0.5 is a **self-hosted, open-source, image generation pipeline** that a developer or brand owner can clone from GitHub, configure with their own API keys, and run locally or on their own server. This is a minimal beta release focused exclusively on image generation. There is no managed cloud and no SaaS offering from the maintainer in v0.5.

A user submits a product image and a structured description — optionally supplemented by a video, 3D model, reference style image, and visual steering parameters. (The company logo is supplied later, at the post-generation overlay step, not at submission.) The system:

1. **Ingests and analyzes the product** — parses all inputs and uses a Vision Agent to produce a structured product profile.
2. **Generates image assets in one of three modes** — the selected mode governs how many images are generated and what artistic direction is used (E-Commerce Batch for catalog shots, A/B Concept Exploration for creative directions, or Seasonal Campaign for holiday-themed images).
3. **Applies logo overlays programmatically** — after generation, the user optionally uploads an SVG or image logo and picks a placement corner; the system composites it onto the generated output.
4. **Refines interactively** — shows the generated image; a refinement loop lets users request changes that an agent translates into revised generation prompts.
5. **Exports assets locally** — saves the approved images to disk, ready for manual use.

---

## What v0.5 Beta Is Not

| Out of Scope for v0.5 Beta | Reason |
|---|---|
| Market research agent | Web search, trend analysis, and crossroads checkpoints deferred to v1.0. |
| Social media posting / publishing | Users export assets and post manually. |
| Copy generation (captions & hashtags) | Deferred to v1.0. |
| Post analytics harvesting | Deferred to future versions. |
| Closed-loop prompt optimization on live posts | Deferred to future versions. |
| Managed cloud / SaaS hosting | v0.5 is self-hosted only. Users bring their own API keys and infrastructure. |
| Billing / subscription management | No revenue infrastructure in beta. |
| Video reel / short-form video production | Deferred to future versions. |
| Mobile app | Web dashboard only. |
| Multi-tenant user management | v0.5 is single-operator per deployment. |

---

## Problem Statement

Creating high-quality, trend-informed product images and copy is:

- **Time-consuming** — requires manual research, briefing designers, setting up shoots, and writing platform-specific copy.
- **Expensive** — agencies charge premium rates; commercial AI SaaS subscriptions add up quickly.
- **Inconsistent** — without a structured creative baseline, visual style and brand voice vary across channels.
- **Unscalable** — brands launching many products cannot manually produce multi-angle shots, platform-optimized copy, and seasonal variants at speed.
- **Closed** — most AI creative tools are locked behind proprietary SaaS walls. Developers and privacy-conscious brands cannot self-host, keep their data private, or customize the agents to their workflow.

This open-source pipeline puts a coordinated team of AI agents directly on any developer's or brand's own machine.

---

## Product Vision

> An open-source, local-first web workspace where a merchant clones a GitHub repo, adds their API keys, uploads a product photo and description, picks an image generation mode (E-Commerce Batch, A/B Concept Exploration, or Seasonal Campaign), and watches the system analyze their inputs and render high-quality, brand-consistent image assets that can be refined in natural language and exported instantly. Market research and copy generation are deferred to v1.0.

---

## Who This Is For

| User Type | Pain Point v0.5 Solves |
|---|---|
| **Open-source developers & hackers** | Want a self-hosted, customizable image generation pipeline they can deploy on their own servers and modify freely. |
| **E-commerce brand owners** | Need standard multi-angle product catalog shots without agency fees. |
| **Digital marketing agencies** | Want a local image asset creation engine they can run to draft product photos for clients at scale. |
| **Privacy-conscious brands** | Require all product images, descriptions, and logos to remain within their own infrastructure. |

---

## How Users Run This

Users interact with this project in three steps:

1. **Clone the repository** from GitHub.
2. **Add their own API keys** to a `.env` file (OpenAI, Anthropic, fal.ai).
3. **Start the stack** with a single `docker compose up` command, then open the dashboard in their browser.

The maintainer provides:
- The full codebase (FastAPI backend + LangGraph agents + Next.js dashboard).
- A `docker-compose.yml` for local setup.
- A setup guide and API key configuration documentation.

The maintainer does **not** provide: any hosted service, managed API keys, or SaaS access in v0.5.

---

## User Flow

```
User opens dashboard (localhost)
        │
        ▼
[SUPERVISION SETTINGS — one-time or per-run]
  Select image generation supervision (manual approval vs. auto-proceed)
        │
        ▼
Upload product media + inputs
  ├── Product Image (JPEG/PNG/WEBP) — REQUIRED
  ├── Product Description (3 structured fields) — REQUIRED
  ├── Product Video (MP4/MOV/WEBM) — optional
  ├── 3D Model (GLTF/OBJ/USDZ) — optional
  ├── Reference Image (style/mood guide) — optional
  └── Visual Steering: aspect ratio, camera angle, lighting preset, negative prompts — optional
  (Company Logo is NOT collected here — it is uploaded later at the post-generation overlay step.)
        │
        ▼
Select Pipeline Mode
  (E-Commerce Batch / A/B Concept Exploration / Seasonal Campaign)
        │
        ▼
Click "Run"
        │
        ▼
  [Ingestion & Processing]
  Vision Agent analyzes product image, reference image, 3D renders, video frames
  Summarizer Agent produces Input Summary Card → shown to user
        │
        ▼
  [CHECKPOINT A — if supervision ON]
  User reviews Input Summary Card
        │
        ▼
  [Image Generation Agent]
  Generates image(s) based on mode; user can then upload a logo + pick a corner to overlay
        │
        ▼
  [CHECKPOINT — if supervision ON]
  Generated image(s) shown to user
  User can: Approve / Request changes (revision loop, max 10 iterations) / Full restart
        │
        ▼
  [FINAL REVIEW DECK — always shown]
  User sees all generated images
  Download images
        │
        ▼
  Assets saved to content/<run_id>/
  Run complete
```

---

## Product Inputs

### Compulsory Inputs

| Input | Format | Details |
|---|---|---|
| **Product Image** | JPEG, PNG, WEBP | Base image used for image-to-image generation. Encoded to Base64 for vision analysis. |
| **Product Description** | Structured text — 3 fields | See below. |

**Product Description — 3 Required Fields:**

1. **Product Info**: Detailed characteristics, key features, name, and USPs. *(e.g., "Organic cold-pressed argan oil in a 30ml amber dropper bottle. Key benefits: anti-aging, moisturizing, lightweight.")*
2. **Target Audience**: Who the product or campaign is aimed at. *(e.g., "Women aged 28–45 interested in natural skincare and clean beauty.")*
3. **Desired Colors**: Specific colors or palette the user wants to dominate the generated image. *(e.g., "Soft pastel pinks, warm cream tones, and matte gold accents.")*

---

### Optional Inputs

| Input | Format | Purpose |
|---|---|---|
| **Product Video** | MP4, MOV, WEBM (max 100MB / 2 min) | FFmpeg extracts keyframes (1 FPS, max 15 frames) to enrich vision analysis with texture, motion, and usage context. |
| **3D Model** | GLTF, OBJ, USDZ | Rendered to 4 high-res thumbnail perspectives (front, back, side, top-down) using a headless Three.js sidecar. Captures accurate geometry and spatial proportions. |
| **Reference Image** | JPEG, PNG, WEBP | Processed during ingestion (downscaled + Base64-encoded), then analyzed by the Vision Agent to extract visual rules: lighting style, composition, depth of field, background type, and overall aesthetic. These rules are injected into the image generation prompt. |

> **Note:** The **company logo is not a submission-time input.** It is uploaded later, at the post-generation Logo Overlay step (see F-4), where the user also selects its placement corner. The logo is never sent to the vision model or the image generator — this saves tokens and avoids the distortion the generative model introduces when a logo is baked into the prompt.

> **v0.5 Note:** Market research is not included in this beta release. Research queries, trend analysis, and brand voice discovery are deferred to v1.0.

---

### Visual Steering Parameters (Optional)

These parameters give the user direct control over the generation output without requiring prompt engineering knowledge. All are optional and have sensible defaults.

| Parameter | Options | Default | Why It Helps |
|---|---|---|---|
| **Aspect Ratio** | `1:1 Square`, `9:16 Vertical`, `16:9 Landscape`, `4:5 Portrait` | `1:1 Square` | Ensures the output matches the target platform's display format before generation, not after cropping. |
| **Camera Perspective** | `Flat Lay (Top-Down)`, `Studio Eye-Level`, `Close-Up Macro`, `Dynamic 3/4 View`, `Hero Shot (Low Angle)` | `Studio Eye-Level` | Directly controls the compositional angle without relying on the LLM to interpret vague descriptions. |
| **Lighting / Vibe Preset** | `Studio Softlight`, `Natural Sunshine`, `Golden Hour Warmth`, `Moody / Chiaroscuro`, `Neon / Cyberpunk`, `Minimalist Pastel` | `Studio Softlight` | Encodes complex lighting setups as a single token injection, producing consistent results without the user needing to describe lighting technique. |
| **Negative Prompts** | Free text | *(empty)* | Explicitly excludes elements the user doesn't want: blurriness, text overlays, extra limbs, watermarks, low resolution. |

---

### Suggested Additional Inputs (Recommended for v1.1 or Strong v1 Candidates)

The following inputs are not currently in scope but would meaningfully improve generation quality and are worth considering before finalizing v1:

| Suggested Input | Why It Matters |
|---|---|
| **Brand Voice / Tone** | A dropdown or short text field (e.g., "Playful & Witty", "Premium & Minimal", "Bold & Energetic") that conditions the image prompt's aesthetic direction. Currently tone is inferred from the product description, which is unreliable. |
| **Campaign Goal** | What the user wants to achieve with this asset (e.g., "Drive product page clicks", "Increase brand awareness", "Announce a launch sale"). Without this, the Image Agent optimizes for generic visual appeal rather than a specific commercial objective. |
| **Competitor or Inspiration Brands** | Names of brands the user admires or competes with (e.g., "similar to Glossier or Aesop"). Used as seed context for the Market Research Agent's initial searches, producing far more targeted trend insights. |
| **Props / Scene Elements** | A free-text field for specifying physical objects to include in the scene (e.g., "marble tray, dried lavender, small candle"). These are injected directly into the image generation prompt and give users compositional control without requiring prompt engineering. |
| **Brand Font / Text Overlay** | Allow the user to specify a short text overlay (tagline or price) and a font file. The overlay would be applied programmatically post-generation (same layer as the logo), avoiding the distortion that occurs when text is baked into AI-generated images. |

---

## Product Features

### F-0 · Multimodal Product Ingestion & Processing

The ingestion layer validates and processes all user inputs before passing them to agents.

**Validation rules:**
- Product Image is required. Reject if absent.
- Product Description: all three fields (Product Info, Target Audience, Desired Colors) are required. Reject if any field is empty.
- Video: validated for codec support and file size (max 100MB, max 2 minutes). Rejected videos surface a clear error.
- 3D Model: validated for supported formats (GLTF, OBJ, USDZ).
- All uploaded files stored in the run's `content/<run_id>/inputs/` directory.

**Processing:**
- Product Image → downscaled and Base64-encoded (JPEG data URI) for LLM vision analysis.
- Reference Image (if provided) → processed during ingestion alongside the product image: downscaled and Base64-encoded (JPEG data URI) for Vision Agent style extraction. Optional and non-fatal — a missing or failed reference image is skipped and the run continues.
- Video → FFmpeg Docker sidecar extracts keyframes at 1 FPS (max 15 frames). Raw video deleted after extraction.
- 3D Model → Headless Three.js/WebGL sidecar renders 4 perspective thumbnails as PNG files.
- Company Logo → **not** ingested or processed at this stage. It is collected at the post-generation Logo Overlay step (F-4) and never passed to the vision model or image generator.

---

### F-1 · AI Vision & Style Analysis

The Vision Agent (GPT-4o Vision) processes all media inputs and produces a unified **Product & Style Profile** JSON, saved to the pipeline's state.

**Inputs processed:**
1. **Product Image** — extracts product category, dominant colors, materials, textures, labels, and existing lighting conditions.
2. **Reference Image (if provided)** — extracts visual rules: inferred design style, background type, lighting technique, composition style, depth of field.
3. **3D Model renders (if provided)** — extracts spatial features and physical geometry for accurate prompt construction.
4. **Video keyframes (if provided)** — multi-frame summary captures the product in motion (texture, usage, reflection).

**Output schema:**

```json
{
  "product_category": "cosmetic bottle",
  "dominant_colors": ["#F5E6D3", "#C8A882"],
  "materials_textures": ["amber glass", "matte black plastic cap"],
  "usps": ["organic cold-pressed oil", "dropper bottle"],
  "inferred_style_from_reference": {
    "vibe": "warm minimalism",
    "background_type": "linen fabric, stone tray",
    "lighting": "golden hour soft side light",
    "composition": "centered product, negative space left side"
  },
  "product_shape": "cylinder",
  "target_audience": "Women aged 28–45 interested in natural skincare",
  "requested_colors": "soft pastel pinks, warm cream, matte gold"
}
```

The Summarizer Agent (Claude Haiku) then merges this profile with the user's description fields into a human-readable **Input Summary Card** shown on the dashboard.

---

### F-2 · Summarizer Agent

The Summarizer Agent (Claude Haiku) merges the product profile from the Vision Agent with the user's description fields into a human-readable **Input Summary Card**. This card is displayed on the dashboard so the user can review and verify that the system correctly understood their product before proceeding to image generation.

**Output schema:**

```json
{
  "product_category": "cosmetic bottle",
  "dominant_colors": ["#F5E6D3", "#C8A882"],
  "materials_textures": ["amber glass", "matte black plastic cap"],
  "usps": ["organic cold-pressed oil", "dropper bottle"],
  "target_audience": "Women aged 28–45 interested in natural skincare",
  "requested_colors": "soft pastel pinks, warm cream, matte gold",
  "inferred_style_from_reference": "warm minimalism with golden hour lighting"
}
```

---

### F-3 · Pipeline Modes

The user selects one mode at submission time. The mode governs the execution path, image quantity, and artistic prompt templates. **v0.5 Beta includes only three modes; market-research-dependent modes are deferred to v1.0.**

---

#### Mode 1: E-Commerce Batch Mode

**When to use:** The user needs a set of clean, catalog-grade product images for Amazon, Shopify, or similar platforms. Speed and volume matter.

**Workflow:** Ingestion → Vision Analysis + Summarizer → Summary Review (if supervision ON) → Image Generation → Export.

**Details:**
- Market Research Agent is **bypassed entirely** — no SerpAPI cost, faster execution.
- Generates **5 to 12 images** (user selects the exact number on submission).
- Prompts are constrained to professional studio photography style: neutral backgrounds (white, off-white, beige, light grey), clean directional lighting, minimalist surfaces (wood, marble, glass), and multi-angle product representation.
- Each of the N images uses a slightly varied scene setup to give the catalog variety without diverging from studio aesthetics.
- **Per-image revision is supported**: the user can select any individual image from the batch and submit a natural language revision request; the Refinement Agent rewrites only that image's prompt and regenerates it (max 10 iterations per image). Other images in the batch remain unchanged.

---

#### Mode 2: A/B Concept Exploration Mode

**When to use:** The user is early in brand positioning and wants to explore visually distinct directions before committing to a style.

**Workflow:** Ingestion → Vision Analysis + Summarizer → Summary Review (if supervision ON) → Image Generation → Export.

**Details:**
- Market Research is bypassed — this mode is intentionally divergent rather than trend-anchored.
- **Concept directions are chosen by the agent by default.** The user may optionally specify concept names/directions via a free-text field on the submission form; if left blank, the Image Agent derives distinct directions from the product profile. This produces faster results without requiring the user to brainstorm positioning hypotheses upfront.
- Generates **3 to 4 images**, each using a completely distinct visual direction. The Image Agent constructs separate prompts for each concept, for example:
  - *Concept A: Mid-Century Modern* — warm walnut surfaces, muted earth tones, geometric props.
  - *Concept B: Hyper-Minimalist Studio* — pure white backdrop, hard shadows, single product focus.
  - *Concept C: Vibrant Maximalist* — bold complementary colors, layered textures, editorial energy.
  - *Concept D: Rustic Outdoors* — natural daylight, moss, stone, botanical props.
- Outputs are labeled by concept name on the dashboard for easy comparison.

---

#### Mode 3: Seasonal / Holiday Campaign Mode

**When to use:** The user wants images for a specific holiday or seasonal moment.

**Workflow:** Ingestion → Vision Analysis + Summarizer → Summary Review (if supervision ON) → Image Generation → Export.

**Details:**
- The user selects a seasonal theme from a dropdown: `Christmas`, `Halloween`, `Summer`, `Spring`, `Diwali`, `Black Friday`, `Valentine's Day`, `Eid`, `Hanukkah`, `New Year`.
- Generates **2 to 3 themed variants**.
- The Image Agent injects season-specific prop tokens, color schemes, and lighting moods (e.g., pine needles, red/green accents, warm ember glow for Christmas; warm bright sunshine, sand textures, and tropical props for Summer).

---

### F-4 · AI Image Generation with Preview & Revision Loop

The Image Agent combines the product profile with the user's visual steering parameters and generates images via FLUX Dev on fal.ai.

**Generation details:**
- **Model**: FLUX Dev via `fal-ai/flux/dev/image-to-image`. The user's product image is used as the base image (image-to-image pipeline), preserving the actual product contours, labels, and geometry.
- **Reference Image style integration**: Style tokens extracted by the Vision Agent from the reference image (lighting, background type, composition) are injected directly into the prompt.
- **Steering parameters**: Aspect ratio, camera perspective, lighting preset, and negative prompts are all appended to the FLUX payload.
- **Quantities**: Governed by the selected mode (see F-3).

**Logo compositing:**
- The logo is collected **at this post-generation step**, not at submission. After the FLUX image is generated, the user optionally uploads a logo (SVG, PNG, or JPEG) and selects its placement corner: `Top-Left`, `Top-Right`, `Bottom-Left` (default), `Bottom-Right`, or `Center Watermark`.
- The logo is never passed to the generative model (which produces distorted, garbled results).
- The **Logo Overlay Node** (Sharp / Canvas in Node.js) then programmatically composites the logo onto the image at the selected corner with a configurable margin and opacity.
- If the user supplies a logo, compositing is re-applied on every revision iteration automatically.

#### User Preview & Revision Loop

Once images (with logo overlays) are generated, they appear on the dashboard:

```
Here is your generated image.

[Image Preview with Logo]

What would you like to change?
[Text input: e.g., "Make the background darker and add more golden lighting"]

[Submit Revision]   [Approve]   [Full Restart]
```

**How revisions work:**

1. The user types a natural language change request.
2. The **Refinement Agent** (Claude Sonnet) takes the original generation prompt, the user's feedback, and the product profile, then rewrites the prompt — injecting the change and removing any contradictory tokens. Example: `"soft grey limestone with side shadows"` → `"vibrant cobalt blue backdrop, studio rim lighting, no shadows"`.
3. The product-preservation tokens (product contours, label accuracy, geometry) are kept intact across all revisions.
4. The revised prompt and original product image are re-submitted to FLUX. The logo is reapplied to the new output.
5. The updated image is displayed. This loop runs up to **10 iterations**.
6. After 10 iterations, the user is prompted to accept the current image or restart.

**Logging**: Every iteration (original prompt, revised prompt, seed, user feedback string, output image path) is written to `run_metadata.json` under `image_iterations`, and the output image is saved as `content/<run_id>/v1.png`, `v2.png`, etc.

---

### F-5 · Final Review Deck & Asset Export

After all revisions are approved, the dashboard displays the **Final Review Deck** — always shown regardless of supervision settings.

**The deck shows:**
- All generated images (full resolution), labeled by mode/concept.
- Per-image download button.

**The user can:**
- Download any or all images to their local machine (saved to `content/<run_id>/`).
- Start a new run.

There is no posting, scheduling, or external API call in v0.5. All exports are local.

---

### F-6 · Web Dashboard (Asset Creation Workspace)

The dashboard is a Next.js 14 (App Router) web application served locally.

**Submission Form:**
- Compulsory: Product Image drag-and-drop zone + 3-part description (Product Info, Target Audience, Desired Colors).
- Optional Media: Video upload, 3D Model upload, Reference Image upload. (Logo upload + corner placement is collected later, at the post-generation Image Revision Canvas / Logo Overlay step — not on this form.)
- Steering Parameters: Aspect Ratio selector, Camera Perspective dropdown, Lighting/Vibe Preset dropdown, Negative Prompts text area.
- Mode Selector: Dropdown for the 3 pipeline modes (E-Commerce Batch, A/B Concept Exploration, Seasonal Campaign).
- Supervision settings panel.

**Live Agent Workspace:**
- Real-time agent execution status tracker (via Server-Sent Events from FastAPI).
- Inline interactive checkpoint cards:
  - **Input Summary Card**: Summarizer's structured overview of the ingested inputs (shown if supervision ON).
  - **Image Revision Canvas**: Generated image(s) with revision chat input, approve, and restart buttons; also offers an optional logo upload + corner placement selector that triggers the post-generation Logo Overlay.
  - **Final Review Deck**: All approved images with per-image download buttons.

---

## Supervision & Control Settings

The user can configure how much human review happens at each checkpoint. This allows fully automated batch generation or precise, hand-guided creative refinement.

| Stage | Supervision ON (Default) | Supervision OFF (Autonomous) |
|---|---|---|
| **Summary Review** | Pauses to show Input Summary Card; user reviews before proceeding to image generation. | Auto-proceeds past summary and goes directly to image generation. |
| **Image Generation** | Shows image(s) with logo overlay; user can approve, revise, or restart. | Auto-approves the first generated image(s) and proceeds. |
| **Final Review Deck** | **Always shown.** User downloads images. | **Always shown.** User downloads images. |

Supervision preferences are saved to a local `workspace_settings.json` file and can be overridden at submission time for a specific run.

---

## Tech Stack

### Cognitive / AI Layer

| Component | Technology | Rationale |
|---|---|---|
| Pipeline Orchestrator | **LangGraph (Python)** | Stateful cyclic graph with first-class human-in-the-loop pause support. Single framework — no CrewAI overlap. |
| Vision Agent LLM | **GPT-4o Vision** | Multimodal analysis of product image, reference image, 3D renders, and video frames. |
| Summarizer Agent LLM | **Claude Haiku** | Fast, low-cost summarization of product profile + description fields into user-readable summary card. |
| Prompt Refinement LLM | **Claude Sonnet** | Translates natural language user feedback into precise, revised image generation prompts. |

### Media / Generation Layer

| Component | Technology | Rationale |
|---|---|---|
| Image Generation | **FLUX Dev via fal.ai** | State-of-the-art image-to-image pipeline; strong prompt adherence and fine detail. Configurable to local GPU in `.env`. |
| 3D Headless Renderer | **Three.js (Node.js headless WebGL)** | Renders GLTF/OBJ/USDZ models to 2D perspective thumbnails without a GPU requirement. |
| Image Compositor | **Sharp (Node.js)** | Programmatic logo/watermark overlay onto generated images. |
| Video Frame Extractor | **FFmpeg** (Docker sidecar) | Lightweight, dependency-free frame extraction from MP4/MOV/WEBM. |

### Data / Memory Layer

| Component | Technology | Rationale |
|---|---|---|
| Run Storage | **Local filesystem (`content/`)** | Each pipeline run writes inputs, outputs, and metadata to its own subfolder. Zero external dependencies. |
| Run Metadata | **`run_metadata.json` (per run)** | Lightweight JSON file inside each run folder recording run config, agent states, iteration history, and output paths. Queryable without a DB. |
| Workspace Settings | **`workspace_settings.json` (local)** | Flat JSON file for supervision defaults and steering presets. Written once; updated in-place. |

### Backend / Infrastructure

| Component | Technology | Rationale |
|---|---|---|
| Agent Server | **Python 3.11+ / FastAPI** | High-performance async backend for LangGraph execution and SSE streaming to the dashboard. |
| 3D Render Sidecar | **Node.js / Express** | Headless WebGL canvas for 3D model loading and thumbnail rendering. |
| Environment / Secrets | **`.env` file (local)** | Self-hosted deployments use a `.env` file with BYO API keys. No external secret manager required in v1. |

### Frontend

| Component | Technology | Rationale |
|---|---|---|
| Framework | **Next.js 14 (App Router)** | Full-stack dashboard with server components and SSE-based real-time updates. |
| UI Components | **shadcn/ui + Tailwind CSS** | Rapid, accessible component development. |
| Real-time Updates | **Server-Sent Events (SSE)** | Streams agent status and checkpoint events from FastAPI to the dashboard without WebSocket complexity. |

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  ASSET CREATION DASHBOARD  (Next.js 14)                  │
│  · Submission Form: Image + Description + Optional Inputs                │
│  · Visual Steering: Aspect Ratio | Camera | Vibe | Negative Prompts      │
│  · Mode Selector: E-Commerce | A/B | Seasonal                            │
│  · Live Agent Workspace: SSE-driven status + inline checkpoint cards     │
└──────────────────────────────────────────────────────────────────────────┘
                                     │  multipart/form-data
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    FastAPI BACKEND  (Python 3.11)                        │
│  · Input validation (required fields, file types, size limits)           │
│  · File storage → /uploads directory                                     │
│  · SSE endpoint for real-time agent status streaming to dashboard        │
└──────────────────────────────────────────────────────────────────────────┘
                  │                                │
                  ▼                                ▼
┌───────────────────────┐              ┌────────────────────────┐
│  FFmpeg Docker sidecar│              │  Three.js Node sidecar │
│  · Extracts keyframes │              │  · Renders 3D model to │
│    from product video │              │    4 PNG perspectives  │
└──────────┬────────────┘              └───────────┬────────────┘
           │  frames[]                             │  thumbnails[]
           └────────────────┬──────────────────────┘
                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│               LANGGRAPH PIPELINE COORDINATOR  (stateful graph)            │
│  · Manages routing between agents based on selected mode                  │
│  · Holds pipeline state (product_profile, summary_card)                   │
│  · Executes human-in-the-loop pause nodes at summary and image checkpoints│
│  · Streams checkpoint events to FastAPI SSE endpoint                      │
└──────┬──────────────────────┬──────────────────────┬──────────────────────┘
       │                      │                      │
       ▼                      ▼
┌──────────────┐   ┌────────────────────┐
│ VISION AGENT │   │ SUMMARIZER AGENT   │
│ GPT-4o Vision│   │ Claude Haiku       │
│ · Product    │   │ · Merges vision    │
│   image      │   │   output + user    │
│ · Reference  │   │   description →    │
│   style      │   │   Input Summary    │
│ · 3D renders │   │   Card JSON        │
│ · Video      │   └────────┬───────────┘
│   frames     │            │
└──────┬───────┘            ▼
       │            [CHECKPOINT A]
       │            User reviews Input Summary Card
       │            (if supervision ON)
       │                    │
       └────────┬───────────┘
                │  Product Profile + User Description
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    IMAGE DESIGNER AGENT                                  │
│  · Constructs FLUX prompt from product profile + steering params         │
│  · Calls fal.ai FLUX Dev image-to-image endpoint (async polling)         │
│  · Applies content moderation gate; retries up to 2x on flagged output   │
└──────────────────────────────────────────────────────────────────────────┘
                                     │  generated image binary
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    LOGO COMPOSITING NODE  (Sharp)                        │
│  · User optionally uploads a logo + picks a corner at this step          │
│  · Programmatically overlays logo at user-specified corner               │
│  · Respects margin + opacity config                                      │
└──────────────────────────────────────────────────────────────────────────┘
                                     │  composite image
                                     ▼
                          [CHECKPOINT B]
                  User previews image; approves or requests revision
┌──────────────────────────────────────────────────────────────────────────┐
│                  REFINEMENT AGENT  (Claude Sonnet)                       │
│  · Rewrites generation prompt based on user's natural language feedback  │
│  · Preserves product-preservation tokens across revisions                │
│  · Loops back to Image Designer Agent (max 10 iterations)                │
└──────────────────────────────────────────────────────────────────────────┘
                                     │  approved image
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  FINAL REVIEW DECK  (always shown)                       │
│  · All approved images displayed on dashboard                            │
│  · Download images → content/<run_id>/                                   │
└──────────────────────────────────────────────────────────────────────────┘
                                     │  run complete
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  LOCAL FILESYSTEM  (content/ directory)                  │
│  content/                                                                │
│  └── <run_id>/                  ← one folder per pipeline run            │
│      ├── inputs/                ← product image, video, model, reference │
│      ├── v1.png … vN.png        ← image iterations (approved = latest)   │
│      └── run_metadata.json      ← full run record (see schema below)     │
│  workspace_settings.json        ← supervision & steering defaults        │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Local Storage Structure

All pipeline data is stored on the local filesystem. No external database is required.

### Directory Layout

```
content/
└── <run_id>/                        ← UUID generated at run start
    ├── inputs/
    │   ├── product_image.jpg        ← uploaded base image (required)
    │   ├── video.mp4                ← optional video
    │   ├── model.gltf               ← optional 3D model
    │   └── reference.jpg            ← optional style reference image
    ├── overlay/
    │   └── logo.png                 ← optional logo, uploaded at the post-generation overlay step (not at submission)
    ├── v1.png                       ← first generated image (logo overlaid if a logo was uploaded)
    ├── v2.png                       ← revision 1 output
    ├── vN.png                       ← approved image = highest vN
    └── run_metadata.json            ← full run record (see schema below)

workspace_settings.json              ← supervision & steering defaults (root of content/)
```

### `run_metadata.json` Schema

Written progressively as the pipeline executes. Each agent node appends or updates its section on completion.

```json
{
  "run_id": "uuid-v4",
  "created_at": "2026-06-17T10:23:00Z",
  "completed_at": "2026-06-17T10:29:45Z",
  "status": "completed",

  "pipeline_mode": "ecommerce",
  "seasonal_theme": null,

  "inputs": {
    "description_product": "...",
    "description_audience": "...",
    "description_colors": "...",
    "image_path": "inputs/product_image.jpg",
    "video_path": "inputs/video.mp4",
    "model_3d_path": null,
    "reference_image_path": "inputs/reference.jpg",
    "reference_image_processed": true
  },

  "steering": {
    "aspect_ratio": "1:1",
    "camera_perspective": "Studio Eye-Level",
    "lighting_preset": "Studio Softlight",
    "negative_prompts": ""
  },

  "supervision": {
    "summary_review": true,
    "image_gen": true
  },

  "agent_states": {
    "product_profile": { },
    "summary_card": { }
  },

  "image_iterations": [
    {
      "version": 1,
      "path": "v1.png",
      "prompt": "...",
      "seed": 42,
      "user_feedback": null
    },
    {
      "version": 2,
      "path": "v2.png",
      "prompt": "...",
      "seed": 99,
      "user_feedback": "make the background darker"
    }
  ],

  "logo_overlay": {
    "logo_path": null,
    "logo_placement": null
  },

  "approved_image": "v2.png",

  "user_rating": null,
  "user_feedback_text": null
}
```

### `workspace_settings.json` Schema

```json
{
  "supervision_defaults": {
    "summary_review": true,
    "image_gen": true
  },
  "default_steering": {
    "aspect_ratio": "1:1",
    "camera_perspective": "Studio Eye-Level",
    "lighting_preset": "Studio Softlight",
    "negative_prompts": ""
  },
  "updated_at": "2026-06-20T09:00:00Z"
}
```

---

## Current Status & Next Steps

### What's Done ✅

**Backend Pipeline (Fully Functional)**
- Text, image, video, and 3D model ingestion and processing
- Vision Agent with provider fallback chain (OpenAI GPT-4o → Anthropic Claude → Google Gemini)
- Summary Agent: generates both the Input Summary Card and creative image generation prompt
- Full integration into LangGraph pipeline with SSE streaming to frontend

**Frontend Submission**
- Complete submission form with all required and optional fields
- Mode selector (3 modes for v0.5: E-Commerce Batch, A/B Concept, Seasonal Campaign)
- Steering parameter selectors (aspect ratio, camera, lighting preset, negative prompts)
- Supervision toggles (summary review, image generation)
- Media upload with client-side processing caching
- Basic processing result screen (shows success/failure summary)

**Testing**
- 21 tests covering Vision Agent and all three providers
- 10 tests covering Summary Agent

### What's Missing / Blocking Progress ⏳

**Critical Blocker: Milestone 2 (Image Generation)**
All downstream milestones depend on completing the Image Designer Agent, FLUX integration, and Revision Loop. Without this, users cannot generate images.

**Highest Priority**
1. Image Designer Agent → constructs FLUX Dev prompts
2. FLUX Dev integration → async polling, content moderation, 2 retries
3. Image Revision Canvas → frontend display of generated image(s)
4. Refinement Agent → rewrites prompts from user feedback
5. Revision loop implementation → max 10 iterations per image

**Next (Milestone 3)**
- Final Review Deck and asset export
- Full E2E testing across all 3 modes, UI polish, and beta GitHub release

### Recommended Next Action

**Build Milestone 2 immediately.** The Image Designer Agent and FLUX integration are the critical path to unblocking the entire product. Once images can be generated, revision loops and market research become feasible.

---

## Milestones & Delivery Plan

### Milestone 0 — Infrastructure Setup *(Week 1–2)*

- [x] Create `content/` directory at repo root; add `.gitkeep`; add `content/*/` to `.gitignore` to exclude run data from version control.
- [x] Initialize `workspace_settings.json` with default supervision and steering values on first launch.
- [x] Implement `RunManager` utility (Python): generates `run_id` (UUID), creates `content/<run_id>/inputs/` directory, initializes `run_metadata.json` with status `"running"`.
- [x] Scaffold Python FastAPI project with LangGraph.
- [x] Scaffold Next.js 14 dashboard (no auth required — single-user local tool).
- [x] Set up FFmpeg Docker sidecar; confirm it starts with `docker compose up`.
- [x] Set up Three.js Node sidecar for 3D model rendering.
- [x] Document `.env` file structure with all required API keys and default values.
- [x] Wire FastAPI SSE endpoint; confirm it streams events to Next.js client.

**Deliverable:** `docker compose up` starts all services; Next.js dashboard loads; SSE connection confirmed in browser; a test run creates a `content/<run_id>/` folder with a valid `run_metadata.json`.

---

### Milestone 1 — Ingestion, Vision Analysis, Summarizer & Image Prompt *(Week 3–4)*

- [x] Build submission form in Next.js: compulsory fields + optional inputs (video, 3D model, reference image; logo is collected later at the overlay step) + steering params + mode selector + supervision panel.
- [x] Build FastAPI ingestion endpoint: validates required fields, file types, and size limits.
- [x] Implement video keyframe extraction via FFmpeg sidecar (1 FPS, max 15 frames).
- [x] Implement 3D model rendering via Three.js sidecar (4 perspective thumbnails).
- [x] Process reference style image during ingestion (downscale + base64) for Vision Agent consumption.
- [x] Build Vision Agent (model-flexible: OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini 2.0): processes product image, reference image, 3D renders, and video frames into `product_profile` JSON with fallback chain and human-in-the-loop checkpoint on failure.
- [x] Build Summarizer Agent (Claude Haiku): merges product profile + description fields into Input Summary Card.
- [x] Build Image Gen Prompt construction: converts product profile + description + steering parameters directly into FLUX-ready prompts (no separate agent in v0.5; embedded in Image Designer Agent).
- [x] Display Input Summary Card on dashboard — rendered inline in the live event log when `summary_complete` fires; full card (product name, category, features, audience, colors, materials, style vibe, vision badge) shown with color swatches and structured layout.
- [x] Write `product_profile` to `run_metadata.json` under `agent_states.product_profile`.
- [x] Write summary card to pipeline state for display at checkpoint.

**Deliverable:** User uploads product image + description; Vision Agent analyzes media with fallback between three models; Summarizer Agent produces Input Summary Card displayed inline in live event log; Image Gen Prompt construction is embedded in Image Designer Agent. ✓ **COMPLETE** — all backend agents wired; Input Summary Card displayed in frontend; image generation interface is Milestone 2.

---

### Milestone 2 — Image Generation with Preview & Revision Loop *(Week 5–6)*

- [ ] Build Image Designer Agent: constructs FLUX prompt from Creative Blueprint + steering parameters.
- [ ] Integrate fal.ai FLUX Dev image-to-image endpoint with async polling.
- [ ] Implement content moderation gate + 2 auto-retries on flagged output.
- [ ] Implement Logo Compositing Node (Sharp): user uploads a logo and selects its placement corner at this post-generation step, then the node applies it at the selected corner.
- [ ] Build Image Revision Canvas on dashboard: shows generated image(s) with approve / revise / restart controls.
- [ ] Build Refinement Agent (Claude Sonnet): rewrites prompt from user's natural language feedback.
- [ ] Implement revision loop (max 10 iterations); save each output as `vN.png` and append iteration record to `run_metadata.json` under `image_iterations`.
- [ ] Implement Full Restart path: clears visual direction, re-runs Image Designer Agent from scratch.
- [ ] Implement all 3 mode-specific generation quantities and prompt templates (E-Commerce Batch: 5-12 images, A/B Concept: 3-4 images, Seasonal: 2-3 images).
- [ ] Implement per-image revision for Mode 1 (E-Commerce Batch): each image in the batch has its own independent revision loop (max 10 iterations per image); revisions to one image do not affect others.

**Status:** In progress. **Priority:** Critical — core feature blocking v0.5 release.

---

### Milestone 3 — Final Review Deck & Beta Release *(Weeks 7–8)*

- [ ] Build Final Review Deck on dashboard: shows all approved images with per-image download buttons.
- [ ] Save approved images to `content/<run_id>/` on user download.
- [ ] Update `run_metadata.json` with `approved_image`, `status: "completed"`, and `completed_at` when the run is finalized.
- [ ] Write `README.md` for v0.5 beta: project overview, prerequisites, `.env` setup, `docker compose up` quick start, API key configuration.
- [ ] Full E2E test across all 3 modes with real product images and videos.
- [ ] Implement pipeline failure handling: any agent error sets `status: "draft"` in `run_metadata.json`; user can resume from the dashboard.
- [ ] Add monitoring: FastAPI logs all agent calls, latencies, and errors to local file.
- [ ] Final UI polish: loading states, error states, empty states, mobile-responsive layout.
- [ ] Create GitHub release (AGPL-3.0 license, `CONTRIBUTING.md`, issue templates).

**Status:** Not started. **Dependency:** Milestone 2 (Image Generation must complete). **Priority:** Critical — blocking beta release.

---

### Deferred to v1.0

**Milestone 4 — Market Research Agent**

The following features are deferred to v1.0:
- Interactive web search via SerpAPI
- Crossroads checkpoint for user-guided research direction selection
- 60-second user question window
- Integration of research findings into creative prompts
- ChromaDB RAG store for search results

---

### Summary Timeline for v0.5 Beta

```
Weeks  1– 2 │ ██████ Milestone 0: Infrastructure
Weeks  3– 4 │ ██████ Milestone 1: Ingestion + Vision + Image Prompt
Weeks  5– 6 │ ██████ Milestone 2: Image Generation + Revision Loop
Weeks  7– 8 │ ██████ Milestone 3: Final Review Deck + Beta Release
```

**Total estimated duration: ~2 months** — Focused, minimal scope.

**v0.5 Data flow:** Input → Ingestion → Vision Analysis → Image Generation → (User Revisions, max 10) → Final Review Deck → Export

---

## Where to Start

1. **Milestone 1 (Ingestion + Vision + Summarizer) is complete.** All backend agents wired; Input Summary Card displayed in frontend.
2. **Build Milestone 2 (Image Generation).** This is the core feature and critical path:
   - Image Designer Agent: constructs FLUX prompts from product profile + steering params.
   - FLUX Dev integration: async polling with content moderation.
   - Refinement Agent: rewrites prompts from user feedback.
   - Revision loop: max 10 iterations per image.
3. **Implement all 3 mode-specific paths in Milestone 2.** The differences are primarily in image quantities and prompt styling — build them in parallel.
4. **Build Milestone 3 (Review Deck + Polish).** Once images generate reliably, finalize the UI and release.

---

## Testing Strategy

### Unit Tests

| Component | Test |
|---|---|
| Input validation | Assert rejection when Product Image or any description field is missing |
| FFmpeg extraction | Assert frame count ≤ 15; assert output files exist |
| 3D sidecar | Assert 4 PNG thumbnails generated for a valid GLTF file |
| Vision Agent | Assert `product_profile` JSON matches Pydantic schema |
| Image Agent — mode quantities | Assert Mode 1 generates 5–12 images; Mode 2 generates 3–4 images; Mode 3 generates 2–3 images |
| Revision loop | Assert revised prompt incorporates user instruction; assert iteration logged to `run_metadata.json` |
| Revision loop cap | Assert "accept current" prompt shown after 10 iterations |
| Logo compositing | Assert logo appears at correct corner in output image; assert compositing re-applied on revision |

### Integration Tests

| Flow | Test |
|---|---|
| Ingestion → Vision | Upload real product image + video; assert `content/<run_id>/run_metadata.json` created with `agent_states.product_profile` populated |
| Vision → Image Generation | Assert FLUX prompt is constructed correctly from product profile + steering parameters |
| Image Generation → Revision | Simulate revision instruction; assert new prompt differs from previous; assert both logged in `run_metadata.json` `image_iterations`; assert `v2.png` exists |
| Mode 1 (E-Commerce) batch | Assert 5–12 images generated; assert all at Studio-style prompt constraints |
| Mode 2 (A/B Concept) | Assert 3–4 images generated with distinct concept labels and differing prompts |
| Mode 3 (Seasonal) | Assert 2–3 images generated with seasonal theme injection |
| Logo overlay | Assert logo file composited onto each generated image at specified corner |
| Image → Review Deck | Assert Review Deck shows all approved images; assert download saves file to `content/<run_id>/` |

### E2E Tests

- Fixed test product (image + video + description + logo + reference image) used for every E2E run.
- Run full pipeline in all 3 modes, all with supervision ON.
- Assert `run_metadata.json` is fully populated (all `agent_states`, `image_iterations`, `approved_image`, `status: "completed"`) after a successful run.
- Assert generated image is visually coherent (manual review step).
- Assert logo is visible and correctly positioned on the output.
- Assert `content/<run_id>/` contains the approved image (`vN.png`) after Review Deck approval.
- Performance target: full supervised pipeline (excluding user think time at checkpoints) completes in **< 6 minutes**.

---

## Risks & Mitigations

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| **R-1** | fal.ai FLUX returns content-flagged output | Medium | Medium | Content moderation gate + 2 auto-retries; escalate to user with clear error message if all retries fail |
| **R-2** | fal.ai async job times out (>5 min) | Medium | Low | Hard 5-minute timeout; save run as `draft`; surface retry button on dashboard |
| **R-3** | User-uploaded video is corrupted or unsupported codec | Medium | High | File validation at ingestion boundary; clear error message with supported format list |
| **R-4** | FFmpeg frame extraction slow for large videos | Low | Medium | 2-minute / 100MB cap enforced at upload; parallel frame extraction |
| **R-5** | GPT-4o Vision produces inaccurate product profile | Medium | Low | Display product profile clearly; user can verify before proceeding to image generation |
| **R-6** | OpenAI / Anthropic / fal.ai API costs spike unexpectedly for self-hosted users | Medium | Low | Document per-run cost estimates prominently in README; add optional hard token budget config in `.env` |
| **R-7** | User revision loop runs indefinitely | Low | Low | Hard cap at 10 revision iterations; "accept current image" prompt displayed after cap is reached |
| **R-8** | 3D model rendering fails on obscure file variants | Low | Medium | Catch Three.js render errors; skip 3D input gracefully and proceed with available inputs; log warning |
| **R-9** | User abandons pipeline mid-run at a checkpoint | Low | Medium | LangGraph state is written to `run_metadata.json` after every node; `status` set to `"draft"`; run folder preserved and resumable from dashboard |
| **R-10** | Logo compositing produces misaligned or disproportionate overlays | Medium | Medium | Configurable margin and max-width constraints in Sharp compositor; preview logo overlay before run in a future update |
| **R-11** | Reference image style extraction is too literal, overriding product identity | Medium | Medium | Vision Agent preserves product-preservation tokens in all prompts; user can exclude reference image via the form |

---

## Success Metrics (KPIs)

### Technical KPIs

| Metric | Target |
|---|---|
| Pipeline success rate (no unhandled errors) | ≥ 95% |
| End-to-end latency — supervised pipeline (excluding user think time) | < 6 minutes |
| End-to-end latency — autonomous pipeline (all supervision OFF) | < 4 minutes |
| Vision analysis: correct product category identification | ≥ 90% |
| Generated image relevance to product profile | ≥ 85% (manual assessment on test set) |
| % of runs where user approves image on first generation (no revision) | ≥ 60% |
| Logo compositing accuracy (logo at correct corner, not distorted) | 100% |

### Community / Adoption KPIs (60 days post GitHub release)

| Metric | Target |
|---|---|
| GitHub stars | ≥ 300 (conservative target for beta) |
| Repository forks | ≥ 50 |
| Community-submitted issues or PRs | ≥ 10 |
| Setup time for a developer with API keys already available | < 15 minutes |

---

## Open Questions

### v0.5 Beta Scope

This beta release focuses exclusively on image generation. The following questions are deferred to v1.0 when market research and copy generation are added:

| # | Question | Deferred to v1.0 |
|---|---|---|
| 1 | Market research — agent or user? | User will optionally trigger research; agent performs web searches and presents findings. |
| 2 | Copy generation — in-pipeline or post-export? | To be decided during v1.0 planning. |
| 3 | Caption Agent — required or optional? | Optional in v1.0. Users can export images without captions. |
| 4 | Multi-reference images? | Single reference image in v0.5 and v1.0. Multi-reference deferred. |

### v0.5 Beta Decisions (Final)

| # | Question | Decision |
|---|---|---|
| 1 | Video-only submission path? | **Closed.** Product Image is strictly required. The system will not proceed without it. No video-to-keyframe fallback. |
| 2 | Mode 2 (A/B Concept) directions: agent or user? | **Closed.** Agent chooses concepts by default. User may optionally specify directions in a free-text field on the submission form. |
| 3 | Run folder disk accumulation? | **Closed.** Pipeline monitors total `content/` size and shows a warning banner when it exceeds 1 GB. No automatic deletion — user controls their data. |
| 4 | Mode 1 revision: per-image or collective? | **Closed.** Per-image revision is supported in v0.5. Each batch image has its own independent revision loop (max 10 iterations). |
| 5 | Logo compositing — post-generation? | **Closed.** Logo is collected and applied after image generation, never sent to the vision model or image generator. |

---

*This document covers v0.5 Beta scope only. Image generation pipeline with 3 modes and revision loops. Market research agent, copy generation, and social publishing deferred to v1.0. See `PRD_v1_Image_Pipeline.md` for the full future roadmap.*

---

**Prepared by:** Antigravity AI & Claude
**Version:** 0.5 Beta — June 20, 2026
