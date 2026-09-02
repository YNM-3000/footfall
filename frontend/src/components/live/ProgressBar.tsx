import "./progress-bar.css";

interface ProgressBarProps {
  processed: number;
  total: number | null;
  status: string;
}

export function ProgressBar({ processed, total, status }: ProgressBarProps) {
  const fraction = total ? Math.min(1, processed / total) : null;

  return (
    <div className="progress">
      <div className="progress__meta">
        <span className={`progress__status progress__status--${status}`}>{status}</span>
        <span className="progress__frames">
          {processed}
          {total ? ` / ${total}` : ""} frames
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
