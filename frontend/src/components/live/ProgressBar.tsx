import { useTranslation } from "react-i18next";

import type { JobStatus } from "../../api/types";
import "./progress-bar.css";

interface ProgressBarProps {
  processed: number;
  total: number | null;
  status: JobStatus;
}

export function ProgressBar({ processed, total, status }: ProgressBarProps) {
  const { t } = useTranslation();
  const fraction = total ? Math.min(1, processed / total) : null;

  return (
    <div className="progress">
      <div className="progress__meta">
        {/* data-status stays language-independent, for styling and tests. */}
        <span className={`progress__status progress__status--${status}`} data-status={status}>
          {t(`status.${status}`)}
        </span>
        <span className="progress__frames">
          {total
            ? t("progress.frames", { processed, total })
            : t("progress.framesUnknown", { processed })}
        </span>
      </div>
      <div
        className="progress__track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={fraction === null ? undefined : Math.round(fraction * 100)}
      >
        <div
          className={`progress__fill${fraction === null ? " progress__fill--indeterminate" : ""}`}
          style={fraction === null ? undefined : { transform: `scaleX(${fraction})` }}
        />
      </div>
    </div>
  );
}
