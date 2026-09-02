import { useEffect, useRef, useState } from "react";

import { getJob, streamUrl } from "../api/client";
import type { Counts, Crossing, JobStatus, StreamMessage } from "../api/types";
import { isTerminal } from "../api/types";

const RECONNECT_DELAY_MS = 1500;
const MAX_FEED_LENGTH = 200;

export interface JobStream {
  status: JobStatus | null;
  counts: Counts;
  processedFrames: number;
  totalFrames: number | null;
  error: string | null;
  crossings: Crossing[];
  connected: boolean;
}

const EMPTY_COUNTS: Counts = { entries: 0, exits: 0, net: 0 };

/**
 * Subscribes to one job's live updates.
 *
 * The socket sends a snapshot on connect, so a reconnect (or a tab opened
 * late) recovers the true state rather than starting from zero.
 */
export function useJobStream(jobId: string | null): JobStream {
  const [state, setState] = useState<JobStream>({
    status: null,
    counts: EMPTY_COUNTS,
    processedFrames: 0,
    totalFrames: null,
    error: null,
    crossings: [],
    connected: false,
  });
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);

  useEffect(() => {
    if (!jobId) {
      setState({
        status: null,
        counts: EMPTY_COUNTS,
        processedFrames: 0,
        totalFrames: null,
        error: null,
        crossings: [],
        connected: false,
      });
      return;
    }

    let cancelled = false;

    const apply = (message: StreamMessage) =>
      setState((previous) => reduce(previous, message));

    const connect = () => {
      if (cancelled) return;
      const socket = new WebSocket(streamUrl(jobId));
      socketRef.current = socket;

      socket.onopen = () => setState((previous) => ({ ...previous, connected: true }));
      socket.onmessage = (event) => apply(JSON.parse(event.data) as StreamMessage);
      socket.onclose = () => {
        setState((previous) => ({ ...previous, connected: false }));
        if (cancelled) return;
        // The server closes the socket when a job ends; only retry while it
        // could still have something to say.
        void getJob(jobId)
          .then((job) => {
            if (!cancelled && !isTerminal(job.status)) {
              reconnectRef.current = window.setTimeout(connect, RECONNECT_DELAY_MS);
            }
          })
          .catch(() => undefined);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
      socketRef.current?.close();
    };
  }, [jobId]);

  return state;
}

function reduce(state: JobStream, message: StreamMessage): JobStream {
  switch (message.type) {
    case "snapshot":
      return {
        ...state,
        status: message.job.status,
        counts: message.job.counts,
        processedFrames: message.job.processed_frames,
        totalFrames: message.job.total_frames,
        error: message.job.error,
      };
    case "progress":
      return { ...state, counts: message.counts, processedFrames: message.processed_frames };
    case "crossing": {
      const { type: _ignored, ...crossing } = message;
      return { ...state, crossings: [crossing, ...state.crossings].slice(0, MAX_FEED_LENGTH) };
    }
    case "status":
      return { ...state, status: message.status, error: message.error };
    default:
      return state;
  }
}
