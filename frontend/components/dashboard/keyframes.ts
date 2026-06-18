// Client-side keyframe extraction: decodes the selected video in a hidden
// <video> element and captures evenly-spaced frames to a <canvas>. This shows
// real frames of the uploaded video in the form preview, before the run (and
// the ffmpeg sidecar's own extraction) happens server-side.

export type Keyframe = { url: string; label: string };

const MAX_EDGE = 1280; // cap thumbnail/lightbox resolution to keep data URLs light

export function formatTime(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function seek(video: HTMLVideoElement, time: number): Promise<void> {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      video.removeEventListener("seeked", finish);
      resolve();
    };
    video.addEventListener("seeked", finish);
    video.currentTime = time;
    // safety net in case 'seeked' never fires
    setTimeout(finish, 3000);
  });
}

export async function extractKeyframes(file: File, count = 6): Promise<Keyframe[]> {
  const objectUrl = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.preload = "auto";
  video.muted = true;
  video.playsInline = true;
  video.src = objectUrl;

  try {
    await new Promise<void>((resolve, reject) => {
      video.onloadeddata = () => resolve();
      video.onerror = () => reject(new Error("Could not decode video"));
      setTimeout(() => reject(new Error("Video load timed out")), 8000);
    });

    const duration = video.duration;
    if (!Number.isFinite(duration) || duration <= 0 || !video.videoWidth) {
      throw new Error("Video has no usable frames");
    }

    const canvas = document.createElement("canvas");
    const scale = Math.min(1, MAX_EDGE / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas unavailable");

    const frames: Keyframe[] = [];
    for (let i = 0; i < count; i++) {
      // spaced across the clip, biased away from the very start/end
      const t = Math.min(duration * ((i + 0.5) / count), Math.max(duration - 0.05, 0));
      await seek(video, t);
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      frames.push({ url: canvas.toDataURL("image/jpeg", 0.8), label: formatTime(t) });
    }
    return frames;
  } finally {
    URL.revokeObjectURL(objectUrl);
    video.removeAttribute("src");
    video.load();
  }
}
