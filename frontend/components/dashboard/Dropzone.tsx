"use client";

import { useId, useRef, useState, type ReactNode } from "react";
import { uploadFile, processUpload, deleteUpload, type PreviewItem } from "@/lib/upload";
import { ImageIcon, VideoIcon, CubeIcon, UploadIcon, XIcon } from "./icons";

type PreviewKind = "image" | "frames" | "views";

// Lifecycle of an asset, surfaced to the parent so it can gate submission.
export type AssetStatus = "empty" | "uploading" | "processing" | "ready" | "error";

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
  onStatus?: (status: AssetStatus) => void;
  onZoom?: (src: string) => void;
  onImageUrl?: (url: string) => void;
};

export function Dropzone({
  fileType, accept, title, sub, preview, icon, maxMB, required, promptIcon,
  onToken, onStatus, onZoom, onImageUrl,
}: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const objUrlRef = useRef<string | null>(null);
  const tokenRef = useRef<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<AssetStatus>("empty");
  const [drag, setDrag] = useState(false);
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  // Server-side processing results (extracted keyframes / rendered views).
  const [items, setItems] = useState<PreviewItem[] | null>(null);
  const reactId = useId();

  const filled = !!file && !error;

  function setStatus(s: AssetStatus) {
    setStage(s);
    onStatus?.(s);
  }

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
      onImageUrl?.(url);
    }
  }

  async function handleFile(f: File | undefined) {
    if (!f) return;
    if (maxMB && f.size > maxMB * 1048576) {
      setFile(f);
      setError(`Too large · max ${maxMB}MB`);
      setImgUrl(null);
      setItems(null);
      revoke();
      onToken(null);
      setStatus("error");
      return;
    }
    setFile(f);
    setError(null);
    setItems(null);
    buildPreview(f);
    onToken(null);
    setStatus("uploading");
    let token: string;
    try {
      token = await uploadFile(f, fileType);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      onToken(null);
      setStatus("error");
      return;
    }
    // Upload succeeded — keep the token even if processing later fails, so the
    // run can retry the asset server-side.
    tokenRef.current = token;
    onToken(token);
    setStatus("processing");
    try {
      const result = await processUpload(token, fileType);
      if (result.status === "error") {
        setError(result.error || "Processing failed");
        setStatus("error");
        return;
      }
      // For frames/views the server is the source of truth — show every frame
      // it actually extracted (not a fixed-size client-side sample).
      if (result.preview && result.preview.kind !== "image") setItems(result.preview.items);
      setStatus("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Processing failed");
      setStatus("error");
    }
  }

  function clearFile(e: React.MouseEvent) {
    e.stopPropagation();
    if (inputRef.current) inputRef.current.value = "";
    if (tokenRef.current) {
      // Drop the token (never submitted) and delete its staged file + cache.
      deleteUpload(tokenRef.current);
      tokenRef.current = null;
    }
    revoke();
    setFile(null);
    setError(null);
    setImgUrl(null);
    setItems(null);
    onToken(null);
    setStatus("empty");
  }

  const meta =
    error ??
    (stage === "uploading"
      ? "uploading…"
      : stage === "processing"
        ? "processing…"
        : file
          ? fmtSize(file.size)
          : "");

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

      {filled && stage !== "uploading" && (
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
                {stage === "processing"
                  ? "Extracting keyframes…"
                  : items && items.length > 0
                    ? `Keyframes extracted · ${items.length}`
                    : "Preview unavailable"}
              </div>
              {items && items.length > 0 && (
                <div className="dz-strip">
                  {items.map((f, i) => (
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
              <div className="dz-preview-label">
                {stage === "processing"
                  ? "Rendering views…"
                  : items && items.length > 0
                    ? `Generated views · ${items.length}`
                    : "Preview unavailable"}
              </div>
              {items && items.length > 0 && (
                <div className="dz-strip">
                  {items.map((v, i) => (
                    <button type="button" key={i} className="dz-frame dz-zoom" onClick={() => onZoom?.(v.url)}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={v.url} alt={v.label} />
                      <span className="flabel">{v.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
