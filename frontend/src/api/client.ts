import type { Crossing, Job, JobRequest, Video } from "./types";

/** Empty by default: Vite proxies /api to the backend in development. */
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as T;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors arrive as a list of field problems.
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
  } catch {
    // Fall through to the status line below.
  }
  return `${response.status} ${response.statusText}`;
}

/**
 * Uploads via XHR rather than fetch: recordings run to hundreds of
 * megabytes, and an upload with no progress feedback reads as a hang.
 */
export function uploadVideo(file: File, onProgress: (fraction: number) => void): Promise<Video> {
  return new Promise((resolve, reject) => {
    const body = new FormData();
    body.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/api/videos`);
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    });
    xhr.addEventListener("load", () => {
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText) as Video);
      } else {
        reject(new Error(parseXhrError(xhr)));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("upload failed — is the API running?")));
    xhr.send(body);
  });
}

function parseXhrError(xhr: XMLHttpRequest): string {
  try {
    return JSON.parse(xhr.responseText).detail ?? `upload failed (${xhr.status})`;
  } catch {
    return `upload failed (${xhr.status})`;
  }
}

export const createJob = (request_: JobRequest): Promise<Job> =>
  request<Job>("/api/jobs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(request_),
  });

export const getJob = (jobId: string): Promise<Job> => request<Job>(`/api/jobs/${jobId}`);

export const listJobs = (): Promise<Job[]> => request<Job[]>("/api/jobs");

export const cancelJob = (jobId: string): Promise<Job> =>
  request<Job>(`/api/jobs/${jobId}/cancel`, { method: "POST" });

export const listCrossings = (jobId: string): Promise<Crossing[]> =>
  request<Crossing[]>(`/api/jobs/${jobId}/crossings`);

export const stillFrameUrl = (videoId: string, index = 0): string =>
  `${BASE}/api/videos/${videoId}/frame.jpg?index=${index}`;

export const previewUrl = (jobId: string, cacheBuster: number): string =>
  `${BASE}/api/jobs/${jobId}/preview.jpg?v=${cacheBuster}`;

export function streamUrl(jobId: string): string {
  const base = BASE || window.location.origin;
  const url = new URL(`/api/jobs/${jobId}/stream`, base);
  url.protocol = url.protocol.replace("http", "ws");
  return url.toString();
}
