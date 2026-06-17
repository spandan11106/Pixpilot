# Pixpilot

An open-source, self-hosted pipeline that takes a product image and description and produces high-quality marketing images and copy using a coordinated team of AI agents.

Upload a product photo, pick a generation mode, and watch Vision → Research → Image Designer agents collaborate to produce on-brand assets — all running on your own infrastructure with your own API keys.

---

## Features

- **5 generation modes** — E-Commerce Batch, Social Media, A/B Concept Exploration, Seasonal Campaign, Summarize & Research Opt-In
- **Multimodal input** — product image, video (keyframe extraction), 3D model (4-angle renders), reference style image, company logo
- **Interactive research** — optional web research agent with live crossroads checkpoints
- **Natural language revision loop** — refine generated images with plain English (up to 10 iterations)
- **Logo compositing** — overlaid programmatically post-generation, never passed to the model
- **Fully local** — all run data stays on your filesystem; no managed cloud

---

## Prerequisites

| Tool | Version |
|---|---|
| Docker + Docker Compose | 24+ |
| Node.js | 20+ |
| Python | 3.11+ |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/pixpilot.git
cd pixpilot

# 2. Add your API keys
cp .env.example .env
# Edit .env and fill in: OPENAI_API_KEY, ANTHROPIC_API_KEY, FAL_API_KEY, SERPAPI_API_KEY

# 3. Start
docker compose up --build
```

Open **http://localhost:3000** in your browser.

---

## API Keys Required

| Key | Where to get it |
|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |
| `FAL_API_KEY` | https://fal.ai/dashboard |
| `SERPAPI_API_KEY` | https://serpapi.com/dashboard |

---

## Architecture

```
frontend/        Next.js 14 dashboard (port 3000)
backend/         FastAPI + LangGraph pipeline (port 8000)
services/
  ffmpeg/        Video keyframe extraction sidecar (port 8001)
  renderer/      Three.js 3D model renderer sidecar (port 8002)
data_processing/ Shared image + text preprocessing utilities
content/         Pipeline run outputs — gitignored, stays local
```

All services start with a single `docker compose up`. Run data is stored under `content/<run_id>/` on your local machine.

---

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, branch conventions, and the PR process.

---

## License

AGPL-3.0 — see [LICENSE](LICENSE).
