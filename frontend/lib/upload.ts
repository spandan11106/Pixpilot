// frontend/lib/upload.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
