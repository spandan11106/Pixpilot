/**
 * Three.js headless 3D model renderer sidecar.
 *
 * Renders 4 perspective thumbnails (front, three-quarter, side, back) of a 3D
 * model so they can be fed to the image-generation model as product context.
 *
 * Rendering is fully off-screen via headless-gl (no browser). Supported formats
 * are GLTF/GLB and OBJ; anything else is rejected with 400 so the backend can
 * treat it as a non-fatal skip.
 */

import express from "express";
import path from "path";
import fs from "fs";

import createGL from "gl";
import { PNG } from "pngjs";
// Three.js binds its animation loop to the global `self` and (cancel)requestAnimationFrame.
// Node has neither, so WebGLRenderer.dispose() crashes on a null context. We render
// one-shot (never start the loop), but dispose() still calls cancelAnimationFrame — so
// provide harmless globals before importing three.
if (typeof globalThis.self === "undefined") globalThis.self = globalThis;
globalThis.requestAnimationFrame =
  globalThis.requestAnimationFrame || ((cb) => setTimeout(() => cb(Date.now()), 16));
globalThis.cancelAnimationFrame =
  globalThis.cancelAnimationFrame || ((id) => clearTimeout(id));

import * as THREE from "three";
import { loadGltf } from "node-three-gltf";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8002;
const RENDER_SIZE = 1024;
const FOV = 45;
// Padding around the product so it nearly fills the frame without touching the
// edges. 1.0 = product corners exactly at the frame edge.
const FRAME_MARGIN = 1.06;

// Camera angles to capture. azimuth rotates around the vertical (Y) axis;
// elevation tilts above the horizon. The three-quarter "hero" view is angled
// up slightly to read as a product shot.
const VIEWS = [
  { name: "front", azimuth: 0, elevation: 0 },
  { name: "three_quarter", azimuth: Math.PI / 4, elevation: Math.PI / 9 },
  { name: "side", azimuth: Math.PI / 2, elevation: 0 },
  { name: "back", azimuth: Math.PI, elevation: 0 },
];

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

/**
 * POST /render-3d
 * Body: { model_path: string, output_dir?: string }
 * Returns: { thumbnails: string[], metrics: {...} } — paths to 4 rendered PNGs
 */
app.post("/render-3d", async (req, res) => {
  const { model_path, output_dir } = req.body;

  if (!model_path) {
    return res.status(400).json({ error: "model_path is required" });
  }
  if (!fs.existsSync(model_path)) {
    return res.status(404).json({ error: `File not found: ${model_path}` });
  }

  const ext = path.extname(model_path).toLowerCase().replace(".", "");
  if (!["gltf", "glb", "obj"].includes(ext)) {
    return res.status(400).json({ error: `unsupported format: ${ext}` });
  }

  const outDir = output_dir || path.join(path.dirname(model_path), "renders");
  // Clear stale renders so the response only reflects this run.
  if (fs.existsSync(outDir)) {
    fs.rmSync(outDir, { recursive: true, force: true });
  }
  fs.mkdirSync(outDir, { recursive: true });

  try {
    const object = await loadModel(model_path, ext);
    const metrics = describeGeometry(object);
    const thumbnails = renderViews(object, outDir);
    res.json({ thumbnails, metrics });
  } catch (err) {
    res.status(422).json({ error: `render failed: ${err.message}` });
  }
});

/** Load a model file into a Three.js Object3D, normalizing for lit rendering. */
async function loadModel(modelPath, ext) {
  if (ext === "obj") {
    const data = fs.readFileSync(modelPath);
    const object = new OBJLoader().parse(data.toString("utf8"));
    // OBJ files often lack normals and materials; supply both so the model is
    // visible under our lighting rather than rendering flat/black.
    object.traverse((child) => {
      if (child.isMesh) {
        if (!child.geometry.attributes.normal) {
          child.geometry.computeVertexNormals();
        }
        child.material = new THREE.MeshStandardMaterial({
          color: 0xcccccc,
          metalness: 0.1,
          roughness: 0.8,
        });
      }
    });
    return object;
  }

  // gltf/glb — node-three-gltf resolves external buffers/textures relative to
  // the file on disk and decodes images via @napi-rs/canvas (no browser/DOM).
  let gltf;
  try {
    gltf = await loadGltf(modelPath);
  } catch (err) {
    const msg = (err && err.message) || String(err);
    if (
      (err && err.code === "ENOENT") ||
      /ENOENT|no such file|Failed to load (buffer|texture)/i.test(msg)
    ) {
      throw new Error(
        `glTF references an external file that was not uploaded (${msg}); ` +
          `upload a self-contained .glb or a .zip of the full glTF folder`
      );
    }
    throw err;
  }
  return gltf.scene;
}

/** Count vertices/faces and the bounding box for the metrics payload. */
function describeGeometry(object) {
  let vertexCount = 0;
  let faceCount = 0;
  object.traverse((child) => {
    if (child.isMesh && child.geometry) {
      const pos = child.geometry.attributes.position;
      if (pos) vertexCount += pos.count;
      const index = child.geometry.index;
      faceCount += index ? index.count / 3 : pos ? pos.count / 3 : 0;
    }
  });
  const box = new THREE.Box3().setFromObject(object);
  const size = new THREE.Vector3();
  box.getSize(size);
  return {
    vertex_count: vertexCount,
    face_count: Math.round(faceCount),
    bounding_box: { x: size.x, y: size.y, z: size.z },
  };
}

/** Render every configured view to a PNG and return the written paths. */
function renderViews(object, outDir) {
  const box = new THREE.Box3().setFromObject(object);
  const center = new THREE.Vector3();
  const sphere = new THREE.Sphere();
  box.getCenter(center);
  box.getBoundingSphere(sphere);
  const radius = sphere.radius || 1;

  // The 8 bounding-box corners, used to frame each view as tightly as possible
  // while still keeping the whole product inside the frame.
  const corners = [];
  for (const cx of [box.min.x, box.max.x]) {
    for (const cy of [box.min.y, box.max.y]) {
      for (const cz of [box.min.z, box.max.z]) {
        corners.push(new THREE.Vector3(cx, cy, cz));
      }
    }
  }

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xffffff);
  // Lower ambient + two directional lights from different angles so faces read
  // at distinct brightnesses and edges stay legible — the form cues the
  // downstream image model relies on.
  scene.add(new THREE.AmbientLight(0xffffff, 0.35));
  const key = new THREE.DirectionalLight(0xffffff, 1.1);
  key.position.set(2, 3, 2);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.5);
  fill.position.set(-2, 1, -1);
  scene.add(fill);
  scene.add(object);

  const camera = new THREE.PerspectiveCamera(FOV, 1, radius * 0.01, radius * 100);

  const renderer = createRenderer();
  const thumbnails = [];
  for (const view of VIEWS) {
    const dir = orbitDirection(view.azimuth, view.elevation);
    const distance = fitDistance(corners, center, dir, FOV, FRAME_MARGIN);
    positionCamera(camera, center, dir, distance);
    renderer.render(scene, camera);
    const filePath = path.join(outDir, `${view.name}.png`);
    writePNG(renderer, filePath);
    thumbnails.push(filePath);
  }
  renderer.dispose();
  return thumbnails;
}

/** Unit vector from the model center toward the camera for a given orbit angle. */
function orbitDirection(azimuth, elevation) {
  return new THREE.Vector3(
    Math.cos(elevation) * Math.sin(azimuth),
    Math.sin(elevation),
    Math.cos(elevation) * Math.cos(azimuth)
  ).normalize();
}

/**
 * Smallest camera distance (along `dir`) that keeps every bounding-box corner
 * inside the frustum, so the product fills the frame as much as possible while
 * remaining wholly visible. FOV is symmetric (square render), so the two axes
 * perpendicular to the view share the same half-angle.
 */
function fitDistance(corners, center, dir, fovDeg, margin) {
  const forward = dir.clone().multiplyScalar(-1); // camera looks toward center
  const worldUp = new THREE.Vector3(0, 1, 0);
  let e1 = new THREE.Vector3().crossVectors(forward, worldUp);
  if (e1.lengthSq() < 1e-6) e1 = new THREE.Vector3(1, 0, 0);
  e1.normalize();
  const e2 = new THREE.Vector3().crossVectors(forward, e1).normalize();
  const t = Math.tan((fovDeg / 2) * (Math.PI / 180));

  let distance = 0;
  for (const c of corners) {
    const v = c.clone().sub(center);
    const depth = v.dot(forward); // signed distance toward the camera's front
    const lateral = Math.abs(v.dot(e1));
    const vertical = Math.abs(v.dot(e2));
    // Need (depth + distance) * t >= lateral|vertical for the corner to be in frame.
    distance = Math.max(distance, lateral / t - depth, vertical / t - depth);
  }
  return distance * margin;
}

/** Place the camera at `distance` along `dir` from center, looking at center. */
function positionCamera(camera, center, dir, distance) {
  camera.position.copy(center).addScaledVector(dir, distance);
  camera.up.set(0, 1, 0);
  camera.lookAt(center);
  camera.updateProjectionMatrix();
}

/** Build an off-screen WebGLRenderer backed by a headless-gl context. */
function createRenderer() {
  const glContext = createGL(RENDER_SIZE, RENDER_SIZE, {
    preserveDrawingBuffer: true,
  });
  const canvas = {
    width: RENDER_SIZE,
    height: RENDER_SIZE,
    style: {},
    addEventListener: () => {},
    removeEventListener: () => {},
    getContext: () => glContext,
  };
  const renderer = new THREE.WebGLRenderer({
    canvas,
    context: glContext,
    antialias: true,
  });
  renderer.setSize(RENDER_SIZE, RENDER_SIZE);
  return renderer;
}

/** Read the rendered frame buffer and write a vertically-flipped PNG. */
function writePNG(renderer, filePath) {
  const gl = renderer.getContext();
  const pixels = new Uint8Array(RENDER_SIZE * RENDER_SIZE * 4);
  gl.readPixels(
    0,
    0,
    RENDER_SIZE,
    RENDER_SIZE,
    gl.RGBA,
    gl.UNSIGNED_BYTE,
    pixels
  );

  const png = new PNG({ width: RENDER_SIZE, height: RENDER_SIZE });
  const rowBytes = RENDER_SIZE * 4;
  // WebGL's origin is bottom-left; PNG's is top-left, so flip rows.
  for (let y = 0; y < RENDER_SIZE; y++) {
    const src = (RENDER_SIZE - 1 - y) * rowBytes;
    png.data.set(pixels.subarray(src, src + rowBytes), y * rowBytes);
  }
  fs.writeFileSync(filePath, PNG.sync.write(png));
}

app.listen(PORT, () => {
  console.log(`Renderer sidecar listening on port ${PORT}`);
});
