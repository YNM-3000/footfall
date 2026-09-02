import { useCallback, useEffect, useMemo, useState } from "react";

import { cancelJob, createJob, listJobs, stillFrameUrl } from "./api/client";
import type { Job, Line, Video } from "./api/types";
import { isTerminal } from "./api/types";
import { horizontalMidline } from "./components/line/geometry";
import { LineEditor } from "./components/line/LineEditor";
import { CountsReadout } from "./components/live/CountsReadout";
import { CrossingFeed } from "./components/live/CrossingFeed";
import { LivePreview } from "./components/live/LivePreview";
import { ProgressBar } from "./components/live/ProgressBar";
import { RunHistory } from "./components/runs/RunHistory";
import type { CountingSettings } from "./components/source/SettingsForm";
import { SettingsForm } from "./components/source/SettingsForm";
import { UploadPanel } from "./components/source/UploadPanel";
import { Panel } from "./components/ui/Panel";
import { useJobStream } from "./hooks/useJobStream";
import "./app.css";

const DEFAULT_SETTINGS: CountingSettings = {
  inDirection: "negative-to-positive",
  // 1280 rather than the model default: on wide 4K shots, 640 misses most of
  // the crowd.
  imgsz: 1280,
  confidence: 0.35,
  frameStride: 1,
};

export default function App() {
  const [video, setVideo] = useState<Video | null>(null);
  const [line, setLine] = useState<Line | null>(null);
  const [settings, setSettings] = useState<CountingSettings>(DEFAULT_SETTINGS);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const stream = useJobStream(jobId);
  const running = stream.status !== null && !isTerminal(stream.status);

  const refreshJobs = useCallback(() => {
    void listJobs()
      .then(setJobs)
      .catch(() => undefined);
  }, []);

  useEffect(refreshJobs, [refreshJobs]);
  useEffect(() => {
    if (stream.status && isTerminal(stream.status)) refreshJobs();
  }, [stream.status, refreshJobs]);

  const onUploaded = (uploaded: Video) => {
    setVideo(uploaded);
    setLine(horizontalMidline(uploaded.width, uploaded.height));
    setJobId(null);
    setError(null);
  };

  const start = async () => {
    if (!video || !line) return;
    setStarting(true);
    setError(null);
    try {
      const job = await createJob({
        video_id: video.id,
        line,
        in_direction: settings.inDirection,
        confidence: settings.confidence,
        imgsz: settings.imgsz,
        frame_stride: settings.frameStride,
        max_frames: null,
      });
      setJobId(job.id);
      refreshJobs();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "could not start the run");
    } finally {
      setStarting(false);
    }
  };

  const stop = async () => {
    if (!jobId) return;
    try {
      await cancelJob(jobId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "could not cancel");
    }
  };

  // Re-fetch the annotated frame whenever counting advances.
  const previewRevision = useMemo(() => stream.processedFrames, [stream.processedFrames]);

  return (
    <div className="app">
      <header className="app__masthead">
        <h1 className="app__title">People Counter</h1>
        <p className="app__subtitle">
          Detection, tracking, and line crossing — configured on the frame, watched live.
        </p>
      </header>

      <main className="app__grid">
        <div className="app__column">
          <Panel title="Source" step="01">
            <UploadPanel video={video} onUploaded={onUploaded} />
          </Panel>

          <Panel title="Counting line" step="02">
            {video && line ? (
              <>
                <LineEditor
                  imageUrl={stillFrameUrl(video.id)}
                  sourceWidth={video.width}
                  sourceHeight={video.height}
                  line={line}
                  invertDirection={settings.inDirection === "positive-to-negative"}
                  onChange={setLine}
                />
                <div className="app__settings">
                  <SettingsForm settings={settings} disabled={running} onChange={setSettings} />
                  <div className="app__actions">
                    <button
                      className="app__primary"
                      type="button"
                      onClick={() => void start()}
                      disabled={running || starting}
                    >
                      {starting ? "Starting…" : running ? "Counting…" : "Start counting"}
                    </button>
                    {running && (
                      <button className="app__secondary" type="button" onClick={() => void stop()}>
                        Stop
                      </button>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <p className="app__placeholder">Upload a recording to place the counting line.</p>
            )}
            {error && (
              <p className="app__error" role="alert">
                {error}
              </p>
            )}
          </Panel>
        </div>

        <div className="app__column">
          <Panel
            title="Live count"
            step="03"
            aside={
              jobId && (
                <span className={`app__link${stream.connected ? " app__link--live" : ""}`}>
                  {stream.connected ? "connected" : "offline"}
                </span>
              )
            }
          >
            {jobId ? (
              <div className="app__live">
                <CountsReadout counts={stream.counts} live={running} />
                <ProgressBar
                  processed={stream.processedFrames}
                  total={stream.totalFrames}
                  status={stream.status ?? "queued"}
                />
                {stream.error && (
                  <p className="app__error" role="alert">
                    {stream.error}
                  </p>
                )}
                <LivePreview jobId={jobId} revision={previewRevision} running={running} />
              </div>
            ) : (
              <p className="app__placeholder">Start a run to watch counts arrive.</p>
            )}
          </Panel>

          <Panel title="Crossings" step="04">
            <CrossingFeed crossings={stream.crossings} />
          </Panel>

          <Panel title="Runs" step="05">
            <RunHistory jobs={jobs} activeJobId={jobId} onSelect={setJobId} />
          </Panel>
        </div>
      </main>
    </div>
  );
}
