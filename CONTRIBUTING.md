# Contributing to Pixpilot

Thank you for taking the time to contribute! Please read this guide before opening a PR.

---

## Prerequisites

| Tool | Version |
|---|---|
| Docker + Docker Compose | 24+ |
| Node.js | 20+ |
| Python | 3.11+ |
| uv | latest (`pip install uv`) |

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-org/pixpilot.git
cd pixpilot

# 2. Copy and fill in your API keys
cp .env.example .env

# 3. Start all services
docker compose up --build
```

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

---

## Working on the Backend (FastAPI / LangGraph)

```bash
cd backend

# Install dependencies
uv sync

# Run locally (outside Docker)
uv run uvicorn app.main:app --reload

# Lint
uv run ruff check .
uv run ruff format .

# Tests
uv run pytest
```

---

## Working on the Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Dev server (outside Docker)
cp .env.local.example .env.local
npm run dev

# Lint
npm run lint
```

---

## Working on Sidecars

**FFmpeg sidecar** (`services/ffmpeg/`) — Python + FastAPI, runs on port 8001.

**Renderer sidecar** (`services/renderer/`) — Node.js + Express, runs on port 8002.

Both are rebuilt automatically with `docker compose up --build`.

---

## Branch Naming

| Type | Pattern |
|---|---|
| Feature | `feat/<short-description>` |
| Bug fix | `fix/<short-description>` |
| Docs | `docs/<short-description>` |
| Chore | `chore/<short-description>` |

---

## Pull Request Process

1. Open an issue first for non-trivial changes so we can align before you invest time.
2. Fork the repo, create a branch, make your changes.
3. Run linting and tests locally before pushing.
4. Fill in the PR template — link the issue, describe the change, check the checklist.
5. A maintainer will review within 3 business days.

---

## Code Style

- **Python**: `ruff` for linting and formatting. Config in `backend/pyproject.toml`.
- **TypeScript**: ESLint + Prettier. Config in `frontend/.eslintrc.json` and `frontend/prettier.config.js`.
- No commented-out code, no unused imports.

---

## Secrets & Security

- **Never commit `.env` or any file containing API keys.**
- `content/` is gitignored — do not force-add run data.
- If you discover a security vulnerability, please email the maintainer privately rather than opening a public issue.

---

## License

By contributing, you agree that your contributions will be licensed under the [AGPL-3.0 License](LICENSE).
