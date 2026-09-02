import type { Crossing } from "../../api/types";
import "./crossing-feed.css";

interface CrossingFeedProps {
  crossings: Crossing[];
}

const formatTimestamp = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const rest = (seconds % 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${rest}`;
};

/** Individual crossings, newest first — the audit trail behind the totals. */
export function CrossingFeed({ crossings }: CrossingFeedProps) {
  if (crossings.length === 0) {
    return <p className="crossing-feed__empty">No crossings yet.</p>;
  }

  return (
    <ol className="crossing-feed">
      {crossings.map((crossing) => (
        <li
          className={`crossing-feed__row crossing-feed__row--${crossing.direction}`}
          key={`${crossing.track_id}-${crossing.frame_index}`}
        >
          <span className="crossing-feed__direction">{crossing.direction}</span>
          <span className="crossing-feed__track">#{crossing.track_id}</span>
          <span className="crossing-feed__time">{formatTimestamp(crossing.timestamp)}</span>
        </li>
      ))}
    </ol>
  );
}
