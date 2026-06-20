# Product Requirements Document — Version 2.0
# Open-Source Multi-Mode Product Image & Copy Generation Pipeline

> **Version:** 2.0
> **Date:** June 17, 2026
> **Status:** Draft — Awaiting Review
>
> **PROGRESS SUMMARY (as of June 20, 2026):**
> - **Milestone 0 (Infrastructure):** ✅ COMPLETE
> - **Milestone 1 (Ingestion + Vision + Summary):** ✅ MOSTLY COMPLETE (backend wired; frontend display of summary card missing)
> - **Milestone 2 (Image Generation + Revision):** ⏳ NOT STARTED
> - **Milestone 3 (Market Research):** ⏳ NOT STARTED
> - **Milestone 4 (Final Review Deck):** ⏳ NOT STARTED
> - **Milestone 5 (Polish + Release):** ⏳ NOT STARTED
>
> **Changelog from v1.2:**
> - Project is fully open-source and self-hosted only. No SaaS deployment, no billing infrastructure, no cloud hosting from the maintainer's side in v1.
> - Social media posting, analytics harvesting, and closed-loop prompt optimization are removed from v1 scope entirely. These are deferred to a future version.
> - Distribution Agent (Ayrshare), Pre-Post Review screen, Analytics Edge Functions, and Evaluator Agent removed from v1.
> - n8n removed from architecture — pipeline runs as a single FastAPI + LangGraph backend.
> - LangGraph is the sole orchestration layer; CrewAI is removed to eliminate framework overlap.
> - Added Reference Image input for style inference.
> - Added additional optional steering inputs: aspect ratio, negative prompts, camera perspective, lighting/vibe preset.
> - Modes revised: Summarization & Research Opt-In, E-Commerce Batch, Social Media Marketing, A/B Concept Exploration, Seasonal Campaign.
> - Revenue model, Ayrshare/Zernio references, deployment_logs, and analytics_history tables removed.

---

## Table of Contents

1. [What v1 Is](#what-v1-is)
2. [What v1 Is Not](#what-v1-is-not)
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
13. [Database Schema](#database-schema)
14. [Current Status & Next Steps](#current-status--next-steps)
15. [Milestones & Delivery Plan](#milestones--delivery-plan)
16. [Where to Start](#where-to-start)
17. [Testing Strategy](#testing-strategy)
18. [Risks & Mitigations](#risks--mitigations)
19. [Success Metrics (KPIs)](#success-metrics-kpis)
20. [Open Questions](#open-questions)

---

## What v1 Is

Version 1 is a **self-hosted, open-source, multi-mode asset generation pipeline** that a developer or brand owner can clone from GitHub, configure with their own API keys, and run locally or on their own server. There is no managed cloud and no SaaS offering from the maintainer in v1.

A user submits a product image and a structured description — optionally supplemented by a video, 3D model, reference style image, and visual steering parameters. (The company logo is supplied later, at the post-generation overlay step, not at submission.) The system:

1. **Ingests and analyzes the product** — parses all inputs and uses a Vision Agent + Summarizer Agent to produce a structured product profile.
2. **Researches the market interactively (optional)** — searches the web in real-time, asks the user clarifying questions with a 1-minute timeout, and presents crossroads decisions for the user to steer the research direction.
3. **Generates image assets in one of five modes** — the selected mode governs how many images are generated, what artistic direction is used, and whether market research runs.
4. **Applies logo overlays programmatically** — after generation, the user optionally uploads an SVG or image logo and picks a placement corner; the system composites it onto the generated output.
5. **Generates copy** — creates platform-optimized captions and hashtags for Instagram, TikTok, Facebook, LinkedIn, and X.
6. **Refines interactively** — shows the generated image and copy; a refinement loop lets users request changes that an agent translates into revised generation prompts.
7. **Exports assets locally** — saves the approved image and copy assets to disk, ready for manual use.

---

## What v1 Is Not

| Out of Scope | Reason |
|---|---|
| Social media posting / publishing | Removed from v1 entirely. Users export assets and post manually. |
| Post analytics harvesting | Depends on posting; deferred with it. |
| Closed-loop prompt optimization on live posts | Depends on analytics; deferred with it. |
| Managed cloud / SaaS hosting | v1 is self-hosted only. Users bring their own API keys and infrastructure. |
| Billing / subscription management | No revenue infrastructure in v1. |
| Video reel / short-form video production | Adds TTS, compositing, and codec complexity; deferred to a future version. |
| Mobile app | Web dashboard only. |
| Multi-tenant user management | v1 is single-operator per deployment. |

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

> An open-source, local-first web workspace where a merchant clones a GitHub repo, adds their API keys, uploads a product photo and description, picks a mode (like E-Commerce or Social Media), and watches an AI agent team summarize their inputs, optionally query live web trends, ask clarifying questions, and render high-quality, brand-consistent image assets and optimized copy — all of which can be refined in natural language and exported instantly.

---

## Who This Is For

| User Type | Pain Point v1 Solves |
|---|---|
| **Open-source developers & hackers** | Want a self-hosted, customizable creative AI pipeline they can deploy on their own servers and modify freely. |
| **E-commerce brand owners** | Need standard multi-angle product catalog shots and marketing copy without agency fees. |
| **Digital marketing agencies** | Want a white-label asset creation engine they can run locally to draft assets for clients at scale. |
| **Privacy-conscious brands** | Require all product images, descriptions, and logos to remain within their own infrastructure. |

---

## How Users Run This

Users interact with this project in three steps:

1. **Clone the repository** from GitHub.
2. **Add their own API keys** to a `.env` file (OpenAI, Anthropic, fal.ai, SerpAPI).
3. **Start the stack** with a single `docker compose up` command, then open the dashboard in their browser.

The maintainer provides:
- The full codebase (FastAPI backend + LangGraph agents + Next.js dashboard).
- A `docker-compose.yml` for local setup.
- A setup guide and API key configuration documentation.

The maintainer does **not** provide: any hosted service, managed API keys, or SaaS access in v1.

---

## User Flow

```
User opens dashboard (localhost)
        │
        ▼
[SUPERVISION SETTINGS — one-time or per-run]
  Select which pipeline stages to review vs. auto-proceed
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
  (E-Commerce Batch / Social Media / A/B Concept / Seasonal / Summarize & Opt-In)
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
  [CHECKPOINT A — Mode 1 / Mode 3 only, if supervision ON]
  User reviews Input Summary Card
  Prompted: "Run Market Research Agent? [Yes] [Skip to image generation]"
        │
        ├── If YES (or Mode 3 with research ON):
        │     ▼
        │   [Market Research Agent — F-3]
        │   Phase 1: 60-second user question window
        │   Phase 2: Web search → Crossroads checkpoint (if applicable)
        │   Phase 3: Final research report approval
        │
        └── If NO / Mode 2 / Mode 4 / Mode 5:
              Skips directly to image generation
        │
        ▼
  [Image Generation Agent — F-4]
  Generates image(s) based on mode; user can then upload a logo + pick a corner to overlay
        │
        ▼
  [CHECKPOINT B — if supervision ON]
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

### F-2 · Pipeline Modes

The user selects one mode at submission time. The mode governs the execution path, image quantity, research involvement, and artistic prompt templates.

---

#### Mode 1: Summarization & Research Opt-In

**When to use:** The user wants to review what the system has understood about their product before committing to a generation path.

**Workflow:** Ingestion → Vision Analysis + Summarizer → **User Pause** → (Optional) Market Research → Image Generation → Export.

**Details:**
- After ingestion and vision analysis, the pipeline pauses and displays the Input Summary Card.
- The user is prompted: *"We've summarized your product. Would you like to run the Market Research Agent before generating? [Run Research] [Skip to Image Generation]"*
- If the user selects **Run Research**, F-3 is invoked. Otherwise the pipeline goes straight to F-4.
- Image quantity: 1 image (social-grade quality).

---

#### Mode 2: E-Commerce Batch Mode

**When to use:** The user needs a set of clean, catalog-grade product images for Amazon, Shopify, or similar platforms. Speed and volume matter over trend research.

**Workflow:** Ingestion → Vision Analysis → Image Generation → Export.

**Details:**
- Market Research Agent is **bypassed entirely** — no SerpAPI cost, faster execution.
- Generates **5 to 12 images** (user selects the exact number on submission).
- Prompts are constrained to professional studio photography style: neutral backgrounds (white, off-white, beige, light grey), clean directional lighting, minimalist surfaces (wood, marble, glass), and multi-angle product representation.
- Each of the N images uses a slightly varied scene setup to give the catalog variety without diverging from studio aesthetics.
- **Per-image revision is supported**: the user can select any individual image from the batch and submit a natural language revision request; the Refinement Agent rewrites only that image's prompt and regenerates it (max 10 iterations per image). Other images in the batch remain unchanged.

---

#### Mode 3: Social Media Marketing Mode

**When to use:** The user wants a single, highly polished marketing image optimized for social feed engagement.

**Workflow:** Ingestion → Vision Analysis → (Optional) Market Research → Image Generation → Export.

**Details:**
- Generates exactly **1 image** optimized for high-engagement social feeds (Instagram, LinkedIn, X, TikTok, Facebook).
- Market research is optional (user toggles at submission). When enabled, the research output directly conditions the image prompt.

---

#### Mode 4: A/B Concept Exploration Mode

**When to use:** The user is early in brand positioning and wants to explore visually distinct directions before committing to a style.

**Workflow:** Ingestion → Vision Analysis → Image Generation → Export.

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

#### Mode 5: Seasonal / Holiday Campaign Mode

**When to use:** The user wants images for a specific holiday or seasonal moment.

**Workflow:** Ingestion → Vision Analysis → Image Generation → Export.

**Details:**
- The user selects a seasonal theme from a dropdown: `Christmas`, `Halloween`, `Summer`, `Spring`, `Diwali`, `Black Friday`, `Valentine's Day`, `Eid`, `Hanukkah`, `New Year`.
- Generates **2 to 3 themed variants**.
- The Image Agent injects season-specific prop tokens, color schemes, and lighting moods (e.g., pine needles, red/green accents, warm ember glow for Christmas; warm bright sunshine, sand textures, and tropical props for Summer).

---

### F-3 · Interactive AI Market Research Agent

Active in **Mode 1** (if opted-in) and **Mode 3** (if opted-in). Operates in three interactive phases.

#### Phase 1 — User Question Checkpoint (60-second timeout)

Before initiating any web searches, the agent pauses and prompts the user:

```
Market Research is about to begin.
Do you have specific questions, competitor brands, or trends you want me to investigate?

[Text input box]                          (Auto-proceeding in 60s…)
```

- A visible countdown timer runs on the dashboard.
- If the user provides input (e.g., "Check how Aesop markets their oils", "Is dark academia aesthetic trending in beauty?"), this context is appended to the agent's search queries.
- If the timer reaches 0 with no input, the agent proceeds automatically using the product profile as the default query basis.

#### Phase 2 — Web Search & Crossroads Checkpoint

- The agent performs real-time web searches via SerpAPI. Results are scraped, cleaned, and stored in a per-run ephemeral ChromaDB vector index.
- If the research surfaces two meaningfully distinct strategic directions, the agent **pauses and asks the user to choose**:

```
I found two distinct angles for this campaign. Which should I prioritize?

  ○ Option A: Sustainable & eco-conscious focus
    (Natural materials, earthy tones, clean beauty positioning)

  ○ Option B: High-performance & results-driven focus
    (Clinical imagery, before/after framing, ingredient science)

[Select]
```

- The pipeline holds until the user selects. Parallel sub-agents then deep-dive only on the chosen path.
- If no meaningful fork exists, Phase 2 completes without interrupting the user.

#### Phase 3 — Research Report Approval

Before the Creative Blueprint is sent to the Image Agent, the Research Agent presents its findings:

```
Research complete. Here is the proposed visual and copy direction:

- Trend: Soft naturalism with warm, earthy tones
- Recommended Scene: Product on slate stone with linen backdrop and dried botanicals
- Top Hooks: "Designed by nature, built for your skin"
- Caption Tone: Conversational, premium, eco-conscious

[Approve & Generate Image]   [Request Changes]
```

- If changes are requested, the user types free-text direction and the agent revises its report.
- On approval, the Creative Blueprint is finalized and passed to F-4.

**Research Agent Output Schema:**

```json
{
  "trending_aesthetic": "soft naturalism with warm tones",
  "top_hooks": ["designed by nature, built for your skin", "the organic shift you've been waiting for"],
  "recommended_keywords": ["#organicliving", "#cleanbeauty", "#minimalhome"],
  "caption_tone": "conversational, premium, eco-conscious",
  "visual_direction": "product resting on slate stone with soft side shadows and linen backdrop",
  "selected_option": "Option A: Sustainable & eco-conscious focus",
  "user_questions_injected": "Check how Aesop markets their oils"
}
```

---

### F-4 · AI Image Generation with Preview & Revision Loop

The Image Agent takes the Creative Blueprint (or raw product profile if research was skipped), combines it with the user's visual steering parameters, and generates images via FLUX Dev on fal.ai.

**Generation details:**
- **Model**: FLUX Dev via `fal-ai/flux/dev/image-to-image`. The user's product image is used as the base image (image-to-image pipeline), preserving the actual product contours, labels, and geometry.
- **Reference Image style integration**: Style tokens extracted by the Vision Agent from the reference image (lighting, background type, composition) are injected directly into the prompt.
- **Steering parameters**: Aspect ratio, camera perspective, lighting preset, and negative prompts are all appended to the FLUX payload.
- **Quantities**: Governed by the selected mode (see F-2).

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

After captions are generated, the dashboard displays the **Final Review Deck** — always shown regardless of supervision settings.

**The deck shows:**
- All generated images (full resolution), labeled by mode/concept.
- Per-image download button.

**The user can:**
- Download any or all images to their local machine (saved to `content/<run_id>/`).
- Start a new run.

There is no posting, scheduling, or external API call in v1. All exports are local.

---

### F-7 · Web Dashboard (Asset Creation Workspace)

The dashboard is a Next.js 14 (App Router) web application served locally.

**Submission Form:**
- Compulsory: Product Image drag-and-drop zone + 3-part description (Product Info, Target Audience, Desired Colors).
- Optional Media: Video upload, 3D Model upload, Reference Image upload. (Logo upload + corner placement is collected later, at the post-generation Image Revision Canvas / Logo Overlay step — not on this form.)
- Steering Parameters: Aspect Ratio selector, Camera Perspective dropdown, Lighting/Vibe Preset dropdown, Negative Prompts text area.
- Mode Selector: Dropdown for the 5 pipeline modes.
- Supervision settings panel.

**Live Agent Workspace:**
- Real-time agent execution status tracker (via Server-Sent Events from FastAPI).
- Inline interactive checkpoint cards:
  - **Input Summary Card**: Summarizer's structured overview of the ingested inputs.
  - **Research Question Checkpoint**: 60-second countdown timer card with text input.
  - **Crossroads Checkpoint**: Two-option selection card.
  - **Research Approval Card**: Full research report with approve/revise controls.
  - **Image Revision Canvas**: Generated image(s) with revision chat input, approve, and restart buttons; also offers an optional logo upload + corner placement selector that triggers the post-generation Logo Overlay.
  - **Final Review Deck**: All approved images with per-image download buttons.

---

## Supervision & Control Settings

The user can configure how much human review happens at each pipeline stage. This allows fully automated batch generation or precise, hand-guided creative refinement.

| Stage | Supervision ON (Default) | Supervision OFF (Autonomous) |
|---|---|---|
| **Market Research** | Pauses at 60s question window, Crossroads selection, and final report approval. | Skips user questions (uses product profile defaults); auto-selects the highest-confidence research path; auto-approves the report. |
| **Image Generation** | Shows image(s) with logo overlay; user can approve, revise, or restart. | Auto-approves the first generated image(s) and proceeds. |
| **Final Review Deck** | **Always shown.** User downloads images. | **Always shown.** User downloads images. |

Supervision preferences are saved to a local `workspace_settings.json` file and can be overridden at submission time for a specific run.

---

## Tech Stack

### Cognitive / AI Layer

| Component | Technology | Rationale |
|---|---|---|
| Pipeline Orchestrator | **LangGraph (Python)** | Stateful cyclic graph with first-class human-in-the-loop pause support. Single framework — no CrewAI overlap. |
| Coordinator / Routing LLM | **OpenAI GPT-4o** | Central brain for state routing, checkpoint decisions, and prompt construction. |
| Vision Agent LLM | **GPT-4o Vision** | Multimodal analysis of product image, reference image, 3D renders, and video frames. |
| Summarizer / Research LLMs | **Anthropic Claude Haiku** | Fast, low-cost, high-quality structured text generation for summarization and research reports. |
| Prompt Refinement LLM | **Claude Sonnet** | Translates natural language user feedback into precise, revised image generation prompts. |
| Web Search | **SerpAPI** | Real-time SERP access for the Market Research Agent. |

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
| Ephemeral RAG Store | **ChromaDB (local SQLite-backed)** | Per-run local vector index for web-scraped research data. Destroyed after run. |

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
│  · Mode Selector: Opt-In | E-Commerce | Social | A/B | Seasonal          │
│  · Live Agent Workspace: SSE-driven status + inline checkpoint cards     │
└──────────────────────────────────────────────────────────────────────────┘
                                     │  multipart/form-data
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    FastAPI BACKEND  (Python 3.11)                         │
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
┌──────────────────────────────────────────────────────────────────────────┐
│               LANGGRAPH PIPELINE COORDINATOR  (stateful graph)           │
│  · Manages routing between agents based on selected mode                 │
│  · Holds pipeline state (product_profile, market_report, blueprint)      │
│  · Executes human-in-the-loop pause nodes at checkpoints                │
│  · Streams checkpoint events to FastAPI SSE endpoint                     │
└──────┬──────────────────────┬──────────────────────┬─────────────────────┘
       │                      │                      │
       ▼                      ▼                      ▼
┌─────────────┐   ┌────────────────────┐   ┌─────────────────────┐
│ VISION AGENT│   │  SUMMARIZER AGENT  │   │ MARKET RESEARCH     │
│ GPT-4o Vision│  │  Claude Haiku      │   │ AGENT               │
│ · Product   │   │  · Merges all      │   │ · Phase 1: 60s Q    │
│   image     │   │    inputs to       │   │   wait              │
│ · Reference │   │    Input Summary   │   │ · SerpAPI searches  │
│   style     │   │    Card JSON       │   │ · ChromaDB RAG      │
│ · 3D renders│   └────────┬───────────┘   │ · Crossroads CP     │
│ · Video     │            │               │ · Report approval   │
│   frames    │            ▼               └──────────┬──────────┘
└──────┬──────┘   [CHECKPOINT A]                      │
       │          User reviews summary;               │ Creative Blueprint
       │          opts in/out of research             │
       │                                              │
       └──────────────────┬───────────────────────────┘
                          │  Product Profile + (optional) Creative Blueprint
                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         IMAGE DESIGNER AGENT                              │
│  · Constructs FLUX prompt from Blueprint + steering params               │
│  · Calls fal.ai FLUX Dev image-to-image endpoint (async polling)         │
│  · Applies content moderation gate; retries up to 2x on flagged output  │
└──────────────────────────────────────────────────────────────────────────┘
                                     │  generated image binary
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         LOGO COMPOSITING NODE  (Sharp)                   │
│  · User optionally uploads a logo + picks a corner at this step           │
│  · Programmatically overlays logo at user-specified corner               │
│  · Respects margin + opacity config                                      │
└──────────────────────────────────────────────────────────────────────────┘
                                     │  composite image
                                     ▼
                          [CHECKPOINT B]
                  User previews image; approves or requests revision
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  REFINEMENT AGENT  (Claude Sonnet)                       │
│  · Rewrites generation prompt based on user's natural language feedback  │
│  · Preserves product-preservation tokens across revisions                │
│  · Loops back to Image Designer Agent (max 10 iterations)               │
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
│  └── <run_id>/                  ← one folder per pipeline run           │
│      ├── inputs/                ← product image, video, model, reference│
│      ├── v1.png … vN.png        ← image iterations (approved = latest)  │
│      └── run_metadata.json      ← full run record (see schema below)    │
│  workspace_settings.json        ← supervision & steering defaults       │
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

  "pipeline_mode": "social",
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
    "research": true,
    "image_gen": true,
    "captions": true
  },

  "agent_states": {
    "product_profile": { },
    "market_report": null,
    "creative_blueprint": { }
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
    "research": true,
    "image_gen": true,
    "captions": true
  },
  "default_steering": {
    "aspect_ratio": "1:1",
    "camera_perspective": "Studio Eye-Level",
    "lighting_preset": "Studio Softlight",
    "negative_prompts": ""
  },
  "updated_at": "2026-06-17T09:00:00Z"
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
- Mode selector (all 5 modes: E-Commerce, Social, A/B, Seasonal, Summarize)
- Steering parameter selectors (aspect ratio, camera, lighting preset, negative prompts)
- Supervision toggles
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

**Later (Milestone 3)**
- Market Research Agent (depends on Image Generation being stable)
- Checkpoint cards for research (60s question, crossroads, approval)

**Finally (Milestone 4 & 5)**
- Final Review Deck and asset export
- Full E2E testing, polish, GitHub release

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
- [x] Build Image Gen Prompt Agent (Claude Sonnet): generates creative blueprint from product profile + description + research (optional) + steering parameters.
- [ ] Display Input Summary Card on dashboard (backend complete; frontend display missing).
- [x] Write `product_profile` to `run_metadata.json` under `agent_states.product_profile`.
- [x] Write `creative_blueprint` to `run_metadata.json` under `agent_states.creative_blueprint`.

**Deliverable:** User uploads product image + description; Vision Agent analyzes media with fallback between three models; Summarizer and Image Gen Prompt Agent produce Input Summary Card and Creative Blueprint. ✓ **MOSTLY COMPLETE** — backend agents wired into graph; frontend display of summary card and image prompt checkpoint needed.

---

### Milestone 2 — Image Generation with Preview & Revision Loop *(Week 5–6)*

- [ ] Build Image Designer Agent: constructs FLUX prompt from Creative Blueprint + steering parameters.
- [ ] Integrate fal.ai FLUX Dev image-to-image endpoint with async polling.
- [ ] Implement content moderation gate + 2 auto-retries on flagged output.
- [ ] Implement Logo Compositing Node (Sharp): user uploads a logo and selects its placement corner at this post-generation step, then the node applies it at the selected corner.
- [ ] Build Image Revision Canvas on dashboard: shows generated image(s) with approve / revise / restart controls.
- [ ] Build Refinement Agent (Claude Sonnet): rewrites prompt from user's natural language feedback.
- [ ] Implement revision loop (max 10 iterations); save each output as `vN.png` and append iteration record to `run_metadata.json` under `image_iterations`.
- [ ] Implement Full Restart path: clears visual direction from Creative Blueprint, re-runs Image Agent.
- [ ] Implement all 5 mode-specific generation quantities and prompt templates (E-Commerce, Social, A/B, Seasonal, Opt-In).
- [ ] Implement per-image revision for Mode 2 (E-Commerce Batch): each image in the batch has its own independent revision loop (max 10 iterations per image); revisions to one image do not affect others.

**Status:** Not started. **Priority:** High — core feature blocking all downstream work.

---

### Milestone 3 — Market Research Agent (Optional, Deferred) *(Week 7–8)*

- [ ] Integrate SerpAPI; implement HTML-to-Markdown scraper and result cleaner.
- [ ] Set up per-run ephemeral ChromaDB instance.
- [ ] Build Phase 1: 60-second question checkpoint card with countdown timer on dashboard.
- [ ] Build Phase 2: SerpAPI search loop; implement Crossroads Checkpoint card (2-option selector) on dashboard.
- [ ] Implement parallel sub-agents for the selected research path.
- [ ] Build Phase 3: Research Report Approval card on dashboard.
- [ ] Integrate research output into Creative Blueprint generation.
- [ ] Write `market_report` to `run_metadata.json` under `agent_states`.

**Status:** Not started. **Dependency:** Milestone 2 (Image Generation) must complete first — research feeds into image generation prompts. **Priority:** Medium (optional in Modes 1 & 3).

---

### Milestone 4 — Final Review Deck *(Week 9–10)*

- [ ] Build Final Review Deck on dashboard: shows all approved images with per-image download buttons.
- [ ] Save approved images to `content/<run_id>/` on user download.
- [ ] Update `run_metadata.json` with `approved_image`, `status: "completed"`, and `completed_at` when the run is finalized.

**Status:** Not started. **Dependency:** Milestone 2 (Image Generation must complete). **Priority:** High — allows users to export final assets.

---

### Milestone 5 — Polish, Testing & GitHub Release *(Week 11–13)*

- [ ] Write full `README.md`: project overview, prerequisites, `.env` setup, `docker compose up` instructions, per-agent configuration guide.
- [ ] Full E2E test across all 5 modes with a real product image.
- [ ] Load test: 3 concurrent pipeline runs without errors.
- [ ] Implement pipeline failure handling: any agent error sets `status: "draft"` in `run_metadata.json`; user can resume from the dashboard.
- [ ] Add monitoring: FastAPI logs all agent calls, latencies, and errors to local file.
- [ ] Implement `content/` directory size check on dashboard load; show persistent warning banner when total size exceeds 1 GB.
- [ ] Performance optimization: Vision Analysis and Market Research run in parallel where mode allows.
- [ ] Final UI polish: loading states, error states, empty states, mobile-responsive layout.
- [ ] Public GitHub release: repository, license (AGPL-3.0), `CONTRIBUTING.md`, issue templates.

**Status:** Not started. **Dependency:** All prior milestones (1–4) must be complete. **Priority:** Final / blocking release.

---

### Summary Timeline

```
Week  1– 2 │ ██████ Milestone 0: Infrastructure
Week  3– 4 │ ██████ Milestone 1: Ingestion + Vision + Summarizer + Image Prompt
Week  5– 6 │ ██████ Milestone 2: Image Generation + Revision Loop
Week  7– 8 │ ██████ Milestone 3: Market Research Agent (Optional, Deferred)
Week  9–10 │ ██████ Milestone 4: Final Review Deck
Week 11–13 │ █████████ Milestone 5: Polish + Testing + GitHub Release
```

**Total estimated duration: ~13 weeks (≈ 3 months)** — Market Research can be added mid-pipeline once core flow is solid.

**Updated data flow:** Input → Processing → Vision Agent → Summary Agent → Image Prompt Agent → Image Generation → (Optional: Market Research) → Final Review

---

## Where to Start

1. **Start with the `RunManager` and `run_metadata.json` schema.** The schema is the contract every agent writes to. Implement the `RunManager` utility (folder creation, `run_metadata.json` initialization, atomic JSON updates) before writing any agent code.
2. **Wire the FFmpeg sidecar and prove video ingestion works.** The video path is the most novel piece of ingestion — validate it early before building agents on top of it.
3. **Build the Vision Agent as a standalone Python function.** Confirm the `product_profile` JSON output matches the Pydantic schema before plugging it into LangGraph.
4. **Build the Market Research Agent standalone and test the interaction loop.** Confirm the crossroads checkpoint and 60-second timer both work end-to-end before touching image generation.
5. **Build the Image Generation Agent last among core agents.** fal.ai FLUX is the most expensive step — only test it once the Creative Blueprint inputs are solid and stable.
6. **Build all five mode execution paths simultaneously in Milestone 3.** The differences between modes are primarily in the prompt template and image quantity — it is cheaper to build them together than to retrofit them one by one.
7. **Do not start on the GitHub release or docs until Milestone 4 is complete and the full pipeline works.** Documentation written against incomplete code will need to be rewritten.

---

## Testing Strategy

### Unit Tests

| Component | Test |
|---|---|
| Input validation | Assert rejection when Product Image or any description field is missing |
| FFmpeg extraction | Assert frame count ≤ 15; assert output files exist |
| 3D sidecar | Assert 4 PNG thumbnails generated for a valid GLTF file |
| Vision Agent | Assert `product_profile` JSON matches Pydantic schema |
| Research Agent — Phase 1 timeout | Assert auto-proceed at 60s when no user input; assert question appended when input provided |
| Research Agent — Crossroads | Assert pipeline pauses when two options detected; assert sub-agents receive only the selected path's context |
| Image Agent — mode quantities | Assert Mode 2 generates 5–12 images; Mode 3 generates 1; Mode 4 generates 3–4; Mode 5 generates 2–3 |
| Revision loop | Assert revised prompt incorporates user instruction; assert iteration logged to `content_ledger` |
| Revision loop cap | Assert "accept current" prompt shown after 10 iterations |
| Logo compositing | Assert logo appears at correct corner in output image; assert compositing re-applied on revision |

### Integration Tests

| Flow | Test |
|---|---|
| Ingestion → Vision | Upload real product image + video; assert `content/<run_id>/run_metadata.json` created with `agent_states.product_profile` populated |
| Vision → Summarizer | Assert Input Summary Card contains data from both Vision Agent and user description fields |
| Research → Blueprint | Assert Creative Blueprint contains `visual_direction` from approved research report |
| Blueprint → Image | Assert FLUX prompt contains visual direction tokens from Creative Blueprint |
| Image revision | Simulate revision instruction; assert new prompt differs from previous; assert both logged in `run_metadata.json` `image_iterations`; assert `v2.png` exists |
| Mode 2 batch | Assert 5 images generated; assert all at Studio-style prompt constraints |
| Mode 4 A/B | Assert 3–4 images generated with distinct concept labels and differing prompts |
| Logo overlay | Assert logo file composited onto each generated image at specified corner |
| Image → Review Deck | Assert Review Deck shows all approved images; assert download saves file to `content/<run_id>/` |

### E2E Tests

- Fixed test product (image + video + description + logo + reference image) used for every E2E run.
- Run full pipeline in all 5 modes, all with supervision ON.
- Assert `run_metadata.json` is fully populated (all `agent_states`, `image_iterations`, `approved_image`, `captions`, `status: "completed"`) after a successful run.
- Assert generated image is visually coherent (manual review step).
- Assert logo is visible and correctly positioned on the output.
- Assert `content/<run_id>/` contains the approved image (`vN.png`) after Review Deck approval.
- Performance target: full supervised pipeline (excluding user think time at checkpoints) completes in **< 6 minutes**.

---

## Risks & Mitigations

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| **R-1** | fal.ai FLUX returns content-flagged output | Medium | Medium | Content moderation gate + 2 auto-retries; escalate to user with clear error message if all retries fail |
| **R-2** | SerpAPI rate limit hit during research | Medium | Medium | Per-query caching in ChromaDB; exponential backoff on 429 errors |
| **R-3** | fal.ai async job times out (>5 min) | Medium | Low | Hard 5-minute timeout; save run as `draft`; surface retry button on dashboard |
| **R-4** | User-uploaded video is corrupted or unsupported codec | Medium | High | File validation at ingestion boundary; clear error message with supported format list |
| **R-5** | FFmpeg frame extraction slow for large videos | Low | Medium | 2-minute / 100MB cap enforced at upload; parallel frame extraction |
| **R-6** | GPT-4o Vision produces inaccurate product profile | Medium | Low | Display Input Summary Card so user can catch and correct misidentification before proceeding |
| **R-7** | OpenAI / Anthropic / fal.ai API costs spike unexpectedly for self-hosted users | Medium | Low | Document per-run cost estimates prominently in README; add optional hard token budget config in `.env` |
| **R-8** | User revision loop runs indefinitely | Low | Low | Hard cap at 10 revision iterations; "accept current image" prompt displayed after cap is reached |
| **R-9** | 3D model rendering fails on obscure file variants | Low | Medium | Catch Three.js render errors; skip 3D input gracefully and proceed with available inputs; log warning |
| **R-10** | User abandons pipeline mid-run at a checkpoint | Low | Medium | LangGraph state is written to `run_metadata.json` after every node; `status` set to `"draft"`; run folder preserved and resumable from dashboard |
| **R-11** | Logo compositing produces misaligned or disproportionate overlays | Medium | Medium | Configurable margin and max-width constraints in Sharp compositor; preview logo overlay before run in a future update |
| **R-12** | Reference image style extraction is too literal, overriding product identity | Medium | Medium | Refinement Agent preserves product-preservation tokens in all prompt revisions; user can exclude reference image via the form |

---

## Success Metrics (KPIs)

### Technical KPIs

| Metric | Target |
|---|---|
| Pipeline success rate (no unhandled errors) | ≥ 95% |
| End-to-end latency — supervised pipeline (excluding user think time) | < 6 minutes |
| End-to-end latency — autonomous pipeline (all supervision OFF) | < 4 minutes |
| Vision analysis: correct product category identification | ≥ 90% |
| Generated image relevance to Creative Blueprint | ≥ 85% (manual assessment on test set) |
| % of runs where user approves image on first generation (no revision) | ≥ 60% |
| Logo compositing accuracy (logo at correct corner, not distorted) | 100% |

### Community / Adoption KPIs (60 days post GitHub release)

| Metric | Target |
|---|---|
| GitHub stars | ≥ 500 |
| Repository forks | ≥ 100 |
| Community-submitted issues or PRs | ≥ 20 |
| Setup time for a developer with API keys already available | < 15 minutes |

---

## Open Questions

All open questions from v2.0 have been resolved. Decisions are recorded below for reference.

| # | Question | Decision |
|---|---|---|
| 1 | Video-only submission path? | **Closed.** Product Image is strictly required. The system will not proceed without it. No video-to-keyframe fallback. |
| 2 | Allow multiple reference images? | **Closed.** Single reference image only in v1. Multi-reference deferred to v2. |
| 3 | Mode 4 concept directions: agent or user? | **Closed.** Agent chooses concepts by default. User may optionally specify directions in a free-text field on the submission form. |
| 4 | Run folder disk accumulation? | **Closed.** Pipeline monitors total `content/` size and shows a warning banner when it exceeds 1 GB. No automatic deletion — user controls their data. |
| 5 | Mode 2 revision: per-image or collective? | **Closed.** Per-image revision is supported in v1. Each batch image has its own independent revision loop (max 10 iterations). |
| 6 | Caption Agent in v1? | **Closed.** Caption generation is removed from v1 entirely. Users export images and write copy manually. |

---

*This document covers v1 scope only. Future versions will introduce social media publishing, post analytics, closed-loop prompt optimization, and video reel production. See `PRD_MultiAgent_Social_Pipeline.md` for the full product roadmap.*

---

**Prepared by:** Antigravity AI & Claude
**Version:** 2.0 — June 17, 2026
