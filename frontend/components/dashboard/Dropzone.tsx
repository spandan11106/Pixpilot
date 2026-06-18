"use client";

import { useId, useRef, useState, type ReactNode } from "react";
import { uploadFile } from "@/lib/upload";
import { extractKeyframes, type Keyframe } from "./keyframes";
import { ImageIcon, VideoIcon, CubeIcon, UploadIcon, XIcon } from "./icons";

type PreviewKind = "image" | "frames" | "views";

const grads = [
  "linear-gradient(135deg,#303ED2,#1B27B4)",
  "linear-gradient(135deg,#EEC04A,#FFAF38)",
  "linear-gradient(135deg,#1B27B4,#303ED2 60%,#EEC04A)",
  "linear-gradient(135deg,#FFAF38,#303ED2)",
  "linear-gradient(135deg,#303ED2,#EEC04A)",
  "linear-gradient(135deg,#B026D3,#303ED2)",
];
const VIEWS = ["Front", "3/4 View", "Side", "Back"];

const fileIcon: Record<"image" | "video" | "cube", ReactNode> = {
  image: <ImageIcon strokeWidth={1.8} />,
  video: <VideoIcon />,
  cube: <CubeIcon />,
};

function fmtSize(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

export type DropzoneProps = {
  fileType: string;
  accept: string;
  title: string;
  sub: string;
  preview: PreviewKind;
  icon: "image" | "video" | "cube";
  maxMB?: number;
  required?: boolean;
  promptIcon?: ReactNode;
  onToken: (token: string | null) => void;
  onZoom?: (src: string) => void;
};

export function Dropzone({
  fileType, accept, title, sub, preview, icon, maxMB, required, promptIcon, onToken, onZoom,
}: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const objUrlRef = useRef<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [drag, setDrag] = useState(false);
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  const [frames, setFrames] = useState<Keyframe[] | null>(null);
  const [framesLoading, setFramesLoading] = useState(false);
  const reactId = useId();

  const filled = !!file && !error;

  function revoke() {
    if (objUrlRef.current) {
      URL.revokeObjectURL(objUrlRef.current);
      objUrlRef.current = null;
    }
  }

  function buildPreview(f: File) {
    if (preview === "image") {
      revoke();
      const url = URL.createObjectURL(f);
      objUrlRef.current = url;
      setImgUrl(url);
    } else if (preview === "frames") {
      setFrames(null);
      setFramesLoading(true);
      extractKeyframes(f)
        .then(setFrames)
        .catch(() => setFrames([])) // graceful: show "no preview" rather than fake tiles
        .finally(() => setFramesLoading(false));
    }
  }

  async function handleFile(f: File | undefined) {
    if (!f) return;
    if (maxMB && f.size > maxMB * 1048576) {
      setFile(f);
      setError(`Too large · max ${maxMB}MB`);
      setImgUrl(null);
      setFrames(null);
      revoke();
      onToken(null);
      return;
    }
    setFile(f);
    setError(null);
    buildPreview(f);
    setUploading(true);
    onToken(null);
    try {
      const token = await uploadFile(f, fileType);
      onToken(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      onToken(null);
    } finally {
      setUploading(false);
    }
  }

  function clearFile(e: React.MouseEvent) {
    e.stopPropagation();
    if (inputRef.current) inputRef.current.value = "";
    revoke();
    setFile(null);
    setError(null);
    setImgUrl(null);
    setFrames(null);
    setFramesLoading(false);
    onToken(null);
  }

  const meta = error ?? (uploading ? "uploading…" : file ? fmtSize(file.size) : "");

  return (
    <div
      className={`dropzone ${filled ? "filled" : ""} ${error ? "dz-error" : ""} ${drag ? "drag" : ""}`}
      onClick={(e) => {
        if ((e.target as HTMLElement).closest(".dz-remove") || (e.target as HTMLElement).closest(".dz-preview")) return;
        inputRef.current?.click();
      }}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files[0]); }}
    >
      <input
        ref={inputRef}
        id={reactId}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {required && <span className="req-tag">Required</span>}

      {!file && (
        <div className="dz-prompt">
          {promptIcon ?? <UploadIcon />}
          <div className="dz-title">{title}</div>
          <div className="dz-sub">{sub}</div>
        </div>
      )}

      {file && (
        <div className="dz-file">
          <span className="fi">{fileIcon[icon]}</span>
          <div style={{ minWidth: 0 }}>
            <div className="dz-name">{file.name}</div>
            <div className="dz-meta">{meta}</div>
          </div>
          <button type="button" className="dz-remove" aria-label="Remove" onClick={clearFile}>
            <XIcon strokeWidth={2} />
          </button>
        </div>
      )}

      {filled && !uploading && (
        <div className="dz-preview" onClick={(e) => e.stopPropagation()}>
          {preview === "image" && imgUrl && (
            <>
              <div className="dz-preview-label">Preview</div>
              <div className="dz-strip">
                <button type="button" className="dz-frame dz-zoom" onClick={() => onZoom?.(imgUrl)}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={imgUrl} alt={file!.name} />
                </button>
              </div>
            </>
          )}

          {preview === "frames" && (
            <>
              <div className="dz-preview-label">
                {framesLoading
                  ? "Extracting keyframes…"
                  : frames && frames.length > 0
                    ? `Keyframes extracted · ${frames.length}`
                    : "Preview unavailable"}
              </div>
              {!framesLoading && frames && frames.length > 0 && (
                <div className="dz-strip">
                  {frames.map((f, i) => (
                    <button type="button" key={i} className="dz-frame dz-zoom" onClick={() => onZoom?.(f.url)}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={f.url} alt={f.label} />
                      <span className="flabel">{f.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}

          {preview === "views" && (
            <>
              <div className="dz-preview-label">Generated views · {VIEWS.length}</div>
              <div className="dz-strip">
                {VIEWS.map((l, i) => (
                  <div key={l} className="dz-frame" style={{ background: grads[i % grads.length] }}>
                    <span className="flabel">{l}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
