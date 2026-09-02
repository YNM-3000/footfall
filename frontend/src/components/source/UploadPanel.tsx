import { useRef, useState } from "react";

import { uploadVideo } from "../../api/client";
import type { Video } from "../../api/types";
import "./upload-panel.css";

interface UploadPanelProps {
  video: Video | null;
  onUploaded: (video: Video) => void;
}

export function UploadPanel({ video, onUploaded }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const upload = async (file: File) => {
    setError(null);
    setProgress(0);
    try {
      onUploaded(await uploadVideo(file, setProgress));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "upload failed");
    } finally {
      setProgress(null);
    }
  };

  const uploading = progress !== null;

  return (
    <div
      className={`upload${dragging ? " upload--dragging" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const file = event.dataTransfer.files[0];
        if (file) void upload(file);
      }}
    >
      <input
        ref={inputRef}
        className="upload__input"
        type="file"
        accept="video/mp4,video/quicktime,video/x-matroska,video/x-msvideo"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void upload(file);
        }}
      />

      {video ? (
        <dl className="upload__meta">
          <div>
            <dt>File</dt>
            <dd title={video.filename}>{video.filename}</dd>
          </div>
          <div>
            <dt>Resolution</dt>
            <dd>
              {video.width}×{video.height}
            </dd>
          </div>
          <div>
            <dt>Frames</dt>
            <dd>
              {video.frame_count ?? "—"} @ {video.fps.toFixed(0)} fps
            </dd>
          </div>
        </dl>
      ) : (
        <p className="upload__prompt">Drop a recording here, or choose a file.</p>
      )}

      <button className="upload__button" type="button" onClick={() => inputRef.current?.click()} disabled={uploading}>
        {uploading ? `Uploading ${Math.round((progress ?? 0) * 100)}%` : video ? "Replace video" : "Choose video"}
      </button>

      {uploading && (
        <div className="upload__bar">
          <div className="upload__bar-fill" style={{ transform: `scaleX(${progress ?? 0})` }} />
        </div>
      )}
      {error && <p className="upload__error" role="alert">{error}</p>}
    </div>
  );
}
