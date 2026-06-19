// frontend/lib/upload.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface PreviewItem {
  url: string;
  label: string;
}

export interface ProcessResult {
  status: "success" | "error";
  file_type: string;
  preview: { kind: "image" | "frames" | "views"; items: PreviewItem[] } | null;
  error: string | null;
}

export async function uploadFile(file: File, fileType: string): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/uploads?file_type=${fileType}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Upload failed: ${res.status}`);
  }
  const { upload_token } = await res.json();
  return upload_token as string;
}

// Process a staged upload immediately (so the run can reuse it and we can show
// real previews). A 200 with status "error" means the asset failed to process.
export async function processUpload(token: string, fileType: string): Promise<ProcessResult> {
  const res = await fetch(`${API_URL}/api/uploads/${token}/process?file_type=${fileType}`, {
    method: "POST",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Processing failed: ${res.status}`);
  }
  return (await res.json()) as ProcessResult;
}

// Delete a staged upload (raw file + cached processing). Best-effort.
export async function deleteUpload(token: string): Promise<void> {
  await fetch(`${API_URL}/api/uploads/${token}`, { method: "DELETE" }).catch(() => {});
}
