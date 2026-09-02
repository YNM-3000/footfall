import type { Counts } from "../../api/types";
import "./counts-readout.css";

interface CountsReadoutProps {
  counts: Counts;
  live: boolean;
}

/**
 * The number an operator reads from across a room. Deliberately the largest
 * thing on the page — everything else is context for it.
 */
export function CountsReadout({ counts, live }: CountsReadoutProps) {
  return (
    <div className="readout">
      <div className="readout__net">
        <span className="readout__label">
          Occupancy
          {live && <span className="readout__pulse" aria-label="live" />}
        </span>
        <output className="readout__value">{counts.net}</output>
      </div>
      <dl className="readout__flows">
        <div className="readout__flow readout__flow--in">
          <dt>In</dt>
          <dd>{counts.entries}</dd>
        </div>
        <div className="readout__flow readout__flow--out">
          <dt>Out</dt>
          <dd>{counts.exits}</dd>
        </div>
      </dl>
    </div>
  );
}
