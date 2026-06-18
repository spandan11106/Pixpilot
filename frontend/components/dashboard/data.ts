// Mock data for the Pixpilot Pipeline Dashboard (frontend-only).
// Mirrors the content from the design source; swap for live API data later.

export type Trend = { dir: "up" | "down"; label: string };

export type Kpi = {
  id: string;
  icon: "image" | "clock" | "target" | "check";
  iconBg: string;
  iconColor: string;
  trend: Trend;
  value: string;
  label: string;
  sparkColor: string;
  sparkPoints: string;
};

export const kpis: Kpi[] = [
  {
    id: "images",
    icon: "image",
    iconBg: "rgba(48,62,210,0.1)",
    iconColor: "var(--primary)",
    trend: { dir: "up", label: "12.4%" },
    value: "14,820",
    label: "Images generated",
    sparkColor: "var(--primary)",
    sparkPoints: "0,28 12,25 24,27 36,20 48,22 60,15 72,13 84,8 100,4",
  },
  {
    id: "render",
    icon: "clock",
    iconBg: "rgba(255,175,56,0.16)",
    iconColor: "#a86b00",
    trend: { dir: "down", label: "3.1%" },
    value: "8.2s",
    label: "Avg. render time",
    sparkColor: "#a86b00",
    sparkPoints: "0,8 12,11 24,9 36,14 48,13 60,18 72,16 84,21 100,24",
  },
  {
    id: "queue",
    icon: "target",
    iconBg: "rgba(238,192,74,0.22)",
    iconColor: "#8a6a00",
    trend: { dir: "up", label: "8 jobs" },
    value: "37",
    label: "In queue",
    sparkColor: "#8a6a00",
    sparkPoints: "0,20 12,12 24,22 36,10 48,24 60,14 72,18 84,9 100,16",
  },
  {
    id: "success",
    icon: "check",
    iconBg: "rgba(30,158,106,0.14)",
    iconColor: "var(--green)",
    trend: { dir: "up", label: "0.6%" },
    value: "99.2%",
    label: "Success rate",
    sparkColor: "var(--green)",
    sparkPoints: "0,12 12,11 24,12 36,9 48,10 60,8 72,9 84,7 100,6",
  },
];

export type Stage = {
  name: string;
  meta: string;
  state: "done" | "active" | "pending";
  label?: string; // dot label when not done (e.g. "3")
};

export const activeJobStages: Stage[] = [
  { name: "Prompt", meta: "Parsed · 0.2s", state: "done" },
  { name: "Queue", meta: "Scheduled · node 03", state: "done" },
  { name: "Rendering", meta: "Step 24 / 30", state: "active", label: "3" },
  { name: "Post-process", meta: "Upscale · face fix", state: "pending", label: "4" },
  { name: "Delivered", meta: "Pending", state: "pending", label: "5" },
];

export type GenStatus =
  | { kind: "done" }
  | { kind: "upscaling" }
  | { kind: "failed"; reason: string };

export type Generation = {
  id: string;
  thumb: string; // thumb class (t1..t6) or "" for failed
  prompt: string;
  meta: string;
  time: string;
  status: GenStatus;
};

export const generations: Generation[] = [
  { id: "g1", thumb: "t1", prompt: "Neon-lit cyberpunk alley, rain reflections, ultra-detailed", meta: "SDXL · 1024²", time: "2m ago", status: { kind: "done" } },
  { id: "g2", thumb: "t2", prompt: "Golden-hour portrait, soft bokeh, warm amber tones", meta: "Flux · 1024²", time: "6m ago", status: { kind: "done" } },
  { id: "g3", thumb: "t3", prompt: "Isometric low-poly island, pastel palette, game asset", meta: "SDXL · 2048²", time: "just now", status: { kind: "upscaling" } },
  { id: "g4", thumb: "t4", prompt: "Minimalist sneaker on pedestal, studio amber backlight", meta: "Flux · 1024²", time: "14m ago", status: { kind: "done" } },
  { id: "g5", thumb: "", prompt: "Watercolor mountain range, misty layers, paper texture", meta: "SD3 · content filter", time: "", status: { kind: "failed", reason: "content filter" } },
  { id: "g6", thumb: "t6", prompt: "Futuristic concept car, chrome body, blue rim light", meta: "SDXL · 1536²", time: "31m ago", status: { kind: "done" } },
];

export type QueueItem = {
  id: string;
  thumb: string;
  title: string;
  progress: number;
  eta: string;
};

export const queueItems: QueueItem[] = [
  { id: "PX-4821", thumb: "t1", title: "#PX-4821 · batch of 4", progress: 80, eta: "~6s left · ETA 14:32" },
  { id: "PX-4822", thumb: "t3", title: "#PX-4822 · upscale 2048²", progress: 42, eta: "~28s left · ETA 14:33" },
  { id: "PX-4823", thumb: "t6", title: "#PX-4823 · batch of 8", progress: 12, eta: "~1m 40s left · ETA 14:35" },
];

export type ActivityItem = {
  id: string;
  avatar: string;
  avatarBg: string;
  avatarColor: string;
  failed?: boolean;
  badge?: string;
  time: string;
  // rendered with simple bold spans; html kept minimal/safe
  body: { text: string; bold?: boolean }[];
};

export const activityItems: ActivityItem[] = [
  {
    id: "a1",
    avatar: "AR",
    avatarBg: "var(--accent-1)",
    avatarColor: "var(--secondary)",
    time: "2m ago",
    body: [
      { text: "Ava Renner", bold: true }, { text: " · " },
      { text: "#PX-4819", bold: true }, { text: " completed — 4 images delivered to " },
      { text: "Marketing", bold: true }, { text: "." },
    ],
  },
  {
    id: "a2",
    avatar: "SY",
    avatarBg: "var(--primary)",
    avatarColor: "var(--surface)",
    time: "9m ago",
    body: [
      { text: "System", bold: true },
      { text: " · Node 07 brought online to absorb the queue spike." },
    ],
  },
  {
    id: "a3",
    avatar: "LM",
    avatarBg: "var(--secondary)",
    avatarColor: "var(--surface)",
    time: "18m ago",
    body: [
      { text: "Leo Mraz", bold: true }, { text: " · published prompt template " },
      { text: "“Studio Product v3”", bold: true }, { text: "." },
    ],
  },
  {
    id: "a4",
    avatar: "!",
    avatarBg: "rgba(220,38,38,0.14)",
    avatarColor: "var(--destructive)",
    failed: true,
    badge: "NSFW flagged",
    time: "24m ago",
    body: [
      { text: "#PX-4815", bold: true }, { text: " failed — " },
    ],
  },
];
