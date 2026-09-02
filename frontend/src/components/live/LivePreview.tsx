import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { previewUrl } from "../../api/client";
import "./live-preview.css";

interface LivePreviewProps {
  jobId: string;
  /** Changes whenever a progress update lands, which re-fetches the frame. */
  revision: number;
  running: boolean;
}

/**
 * The latest annotated frame, pulled as a plain image.
 *
 * Deliberately not a video stream: the backend re-encodes at most twice a
 * second at preview width, so this costs a fraction of what streaming 4K
 * would, and it is enough to confirm the boxes and the gate look right.
 */
export function LivePreview({ jobId, revision, running }: LivePreviewProps) {
  const { t } = useTranslation();
  const [failed, setFailed] = useState(false);

  // A job that has not produced a frame yet has no preview to serve; reset
  // the failure state whenever a new frame could exist.
  useEffect(() => setFailed(false), [jobId, revision]);

  if (revision === 0 || failed) {
    return (
      <p className="live-preview__pending">
        {running ? t("preview.waiting") : t("preview.none")}
      </p>
    );
  }

  return (
    <figure className="live-preview">
      <img
        className="live-preview__image"
        src={previewUrl(jobId, revision)}
        alt={t("preview.alt")}
        onError={() => setFailed(true)}
      />
      <figcaption className="live-preview__caption">
        {running ? t("preview.running") : t("preview.finished")}
      </figcaption>
    </figure>
  );
}
