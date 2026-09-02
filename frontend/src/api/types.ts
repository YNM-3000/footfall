export type Direction = "in" | "out";

export type InDirection = "negative-to-positive" | "positive-to-negative";

export interface Video {
  id: string;
  filename: string;
  width: number;
  height: number;
  fps: number;
  frame_count: number | null;
  created_at: string;
}

export interface Counts {
  entries: number;
  exits: number;
  net: number;
}

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface Job {
  id: string;
  video_id: string;
  status: JobStatus;
  counts: Counts;
  processed_frames: number;
  total_frames: number | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  config: Record<string, unknown>;
}

export interface Crossing {
  track_id: number;
  direction: Direction;
  frame_index: number;
  timestamp: number;
}

/** Counting line endpoints, in source-video pixel coordinates. */
export type Line = [number, number, number, number];

export interface JobRequest {
  video_id: string;
  line: Line | null;
  in_direction: InDirection;
  confidence: number;
  imgsz: number | null;
  frame_stride: number;
  max_frames: number | null;
}

export type StreamMessage =
  | { type: "snapshot"; job: Job }
  | { type: "progress"; processed_frames: number; counts: Counts }
  | ({ type: "crossing" } & Crossing)
  | { type: "status"; status: JobStatus; error: string | null };

export const TERMINAL_STATUSES: JobStatus[] = ["completed", "failed", "cancelled"];

export const isTerminal = (status: JobStatus): boolean => TERMINAL_STATUSES.includes(status);
