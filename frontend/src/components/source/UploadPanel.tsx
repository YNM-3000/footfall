import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { uploadVideo } from "../../api/client";
import type { Video } from "../../api/types";
import "./upload-panel.css";

interface UploadPanelProps {
  video: Video | null;
  onUploaded: (video: Video) => void;
}

export function UploadPanel({ video, onUploaded }: UploadPanelProps) {
  const { t } = useTranslation();
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
      setError(cause instanceof Error ? cause.message : t("upload.failed"));
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
            <dt>{t("upload.file")}</dt>
            <dd title={video.filename}>{video.filename}</dd>
          </div>
          <div>
            <dt>{t("upload.resolution")}</dt>
            <dd>
              {video.width}×{video.height}
            </dd>
          </div>
          <div>
            <dt>{t("upload.frames")}</dt>
            <dd>
              {t("upload.framesValue", {
                count: video.frame_count ?? "—",
                fps: video.fps.toFixed(0),
              })}
            </dd>
          </div>
        </dl>
      ) : (
        <p className="upload__prompt">{t("upload.prompt")}</p>
      )}

      <button className="upload__button" type="button" onClick={() => inputRef.current?.click()} disabled={uploading}>
        {uploading
          ? t("upload.uploading", { percent: Math.round((progress ?? 0) * 100) })
          : t(video ? "upload.replace" : "upload.choose")}
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
