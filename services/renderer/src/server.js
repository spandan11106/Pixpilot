/**
 * Three.js headless 3D model renderer sidecar.
 * Stub for Milestone 0 — returns placeholder thumbnails.
 * Full Three.js/WebGL implementation in Milestone 1.
 */

const express = require("express");
const path = require("path");
const fs = require("fs");

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8002;

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

/**
 * POST /render-3d
 * Body: { model_path: string, output_dir: string }
 * Returns: { thumbnails: string[] } — paths to 4 rendered PNGs
 *
 * Perspectives: front, back, side, top-down
 */
app.post("/render-3d", (req, res) => {
  const { model_path, output_dir } = req.body;

  if (!model_path) {
    return res.status(400).json({ error: "model_path is required" });
  }

  if (!fs.existsSync(model_path)) {
    return res.status(404).json({ error: `File not found: ${model_path}` });
  }

  const outDir = output_dir || path.join(path.dirname(model_path), "renders");
  fs.mkdirSync(outDir, { recursive: true });

  // Stub: return expected output paths (actual rendering in Milestone 1)
  const perspectives = ["front", "back", "side", "top"];
  const thumbnails = perspectives.map((p) => path.join(outDir, `${p}.png`));

  res.json({ thumbnails, message: "stub — full rendering implemented in Milestone 1" });
});

app.listen(PORT, () => {
  console.log(`Renderer sidecar listening on port ${PORT}`);
});
