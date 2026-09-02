import { useTranslation } from "react-i18next";

import type { Job } from "../../api/types";
import "./run-history.css";

interface RunHistoryProps {
  jobs: Job[];
  activeJobId: string | null;
  onSelect: (jobId: string) => void;
}

/**
 * Past runs. With one uploaded clip this is a history list; with several
 * live cameras the same shape becomes the tile grid.
 */
export function RunHistory({ jobs, activeJobId, onSelect }: RunHistoryProps) {
  const { t, i18n } = useTranslation();

  if (jobs.length === 0) {
    return <p className="runs__empty">{t("runs.empty")}</p>;
  }

  return (
    <ul className="runs">
      {jobs.map((job) => (
        <li key={job.id}>
          <button
            type="button"
            className={`runs__item${job.id === activeJobId ? " runs__item--active" : ""}`}
            onClick={() => onSelect(job.id)}
            aria-current={job.id === activeJobId}
          >
            <span className={`runs__status runs__status--${job.status}`}>{t(`status.${job.status}`)}</span>
            <span className="runs__counts">
              <span className="runs__in">+{job.counts.entries}</span>
              <span className="runs__out">−{job.counts.exits}</span>
              <span className="runs__net">= {job.counts.net}</span>
            </span>
            <time className="runs__time" dateTime={job.created_at}>
              {new Date(job.created_at).toLocaleTimeString(i18n.language)}
            </time>
          </button>
        </li>
      ))}
    </ul>
  );
}
