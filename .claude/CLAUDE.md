# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pixpilot is a data pipeline for AI-assisted marketing. It preprocesses images and markdown text to produce clean, optimized payloads suitable for vision model consumption.

## Rules

- All agent instruction files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, etc.) must live exclusively inside `.claude/`. Never create or leave these files anywhere else in the repository.

## Running Tests

Tests live in `testing/` and are run as scripts (not a test framework like pytest). Run from the repo root so relative imports resolve:

```bash
python -m testing.test_image
python -m testing.test_text
```

Each test script auto-generates mock input in `./testing_input/` if the files don't already exist.

## Architecture

`data_processing/` contains two processing modules:

- **`image.py`** — `process_image(file_path, max_longest_edge=1024)`: validates format (jpg/jpeg/png/webp), converts RGBA/P to RGB, thumbnails to fit within `max_longest_edge`, encodes to JPEG base64 data URI. Returns a dict with `status`, `filename`, `metrics`, and `image_payload`.

- **`text.py`** — `process_markdown(file_path)`: reads a `.md` file, strips zero-width unicode chars, removes URLs (both naked and markdown-linked), normalizes whitespace and line breaks. Returns a dict with `status`, `filename`, `metrics`, and `content`.

Both functions raise `FileNotFoundError` for missing files and `ValueError`/`RuntimeError` for invalid input or processing failures. Return shape is always `{"status": "success", "filename": ..., "metrics": {...}, ...}`.

## Dependencies

Requires `Pillow` for image processing. No requirements file exists yet — install manually:

```bash
pip install Pillow
```
