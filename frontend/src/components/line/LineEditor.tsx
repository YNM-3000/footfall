import { useCallback, useRef, useState } from "react";
import { Trans, useTranslation } from "react-i18next";

import type { Line } from "../../api/types";
import { useElementSize } from "../../hooks/useElementSize";
import { clamp, inwardArrow, withEnd, withStart } from "./geometry";
import "./line-editor.css";

type Handle = "start" | "end" | null;

interface LineEditorProps {
  imageUrl: string;
  sourceWidth: number;
  sourceHeight: number;
  line: Line;
  invertDirection: boolean;
  onChange: (line: Line) => void;
}

const HANDLE_RADIUS_FRACTION = 0.018;
const ARROW_LENGTH_FRACTION = 0.09;

/**
 * Draws the counting gate on a still frame.
 *
 * Counting accuracy depends more on this line than on any other setting, and
 * picking pixel coordinates by hand is the worst part of the CLI — so the
 * frame is the control surface: drag either endpoint, watch the IN arrow.
 */
export function LineEditor({
  imageUrl,
  sourceWidth,
  sourceHeight,
  line,
  invertDirection,
  onChange,
}: LineEditorProps) {
  const { t } = useTranslation();
  const [wrapperRef, size] = useElementSize<HTMLDivElement>();
  const [dragging, setDragging] = useState<Handle>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const toSourcePoint = useCallback(
    (clientX: number, clientY: number) => {
      const bounds = svgRef.current?.getBoundingClientRect();
      if (!bounds || bounds.width === 0) return null;
      return {
        x: clamp(((clientX - bounds.left) / bounds.width) * sourceWidth, 0, sourceWidth),
        y: clamp(((clientY - bounds.top) / bounds.height) * sourceHeight, 0, sourceHeight),
      };
    },
    [sourceHeight, sourceWidth],
  );

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!dragging) return;
    const point = toSourcePoint(event.clientX, event.clientY);
    if (!point) return;
    onChange(dragging === "start" ? withStart(line, point) : withEnd(line, point));
  };

  const startDrag = (handle: Handle) => (event: React.PointerEvent<SVGCircleElement>) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(handle);
  };

  const nudge = (handle: Exclude<Handle, null>, dx: number, dy: number) => {
    const point =
      handle === "start"
        ? { x: clamp(line[0] + dx, 0, sourceWidth), y: clamp(line[1] + dy, 0, sourceHeight) }
        : { x: clamp(line[2] + dx, 0, sourceWidth), y: clamp(line[3] + dy, 0, sourceHeight) };
    onChange(handle === "start" ? withStart(line, point) : withEnd(line, point));
  };

  const handleRadius = Math.max(sourceWidth, sourceHeight) * HANDLE_RADIUS_FRACTION;
  const arrow = inwardArrow(line, invertDirection, Math.min(sourceWidth, sourceHeight) * ARROW_LENGTH_FRACTION);

  return (
    <div className="line-editor" ref={wrapperRef}>
      <div className="line-editor__stage">
        <img className="line-editor__frame" src={imageUrl} alt={t("line.frameAlt")} />
        <svg
          ref={svgRef}
          className="line-editor__overlay"
          viewBox={`0 0 ${sourceWidth} ${sourceHeight}`}
          preserveAspectRatio="none"
          onPointerMove={handlePointerMove}
          onPointerUp={() => setDragging(null)}
          onPointerLeave={() => setDragging(null)}
          role="group"
          aria-label={t("line.editorLabel")}
        >
          <defs>
            <marker id="arrowhead" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
              <path d="M0,0 L4,2 L0,4 Z" fill="var(--accent-in)" />
            </marker>
          </defs>

          <line
            className="line-editor__gate"
            x1={line[0]}
            y1={line[1]}
            x2={line[2]}
            y2={line[3]}
            strokeWidth={handleRadius * 0.35}
          />
          <line
            className="line-editor__arrow"
            x1={arrow.from.x}
            y1={arrow.from.y}
            x2={arrow.to.x}
            y2={arrow.to.y}
            strokeWidth={handleRadius * 0.3}
            markerEnd="url(#arrowhead)"
          />

          {(["start", "end"] as const).map((handle) => {
            const cx = handle === "start" ? line[0] : line[2];
            const cy = handle === "start" ? line[1] : line[3];
            return (
              <circle
                key={handle}
                className="line-editor__handle"
                cx={cx}
                cy={cy}
                r={handleRadius}
                tabIndex={0}
                role="slider"
                aria-label={`${handle} of counting line`}
                aria-valuetext={`x ${Math.round(cx)}, y ${Math.round(cy)}`}
                onPointerDown={startDrag(handle)}
                onKeyDown={(event) => {
                  const step = event.shiftKey ? 50 : 10;
                  const moves: Record<string, [number, number]> = {
                    ArrowLeft: [-step, 0],
                    ArrowRight: [step, 0],
                    ArrowUp: [0, -step],
                    ArrowDown: [0, step],
                  };
                  const move = moves[event.key];
                  if (!move) return;
                  event.preventDefault();
                  nudge(handle, move[0], move[1]);
                }}
              />
            );
            })}
        </svg>
      </div>
      <p className="line-editor__hint">
        <Trans i18nKey="line.hint" components={{ 1: <strong /> }} />{" "}
        {size.width > 0 &&
          t("line.dimensions", {
            preview: Math.round(size.width),
            width: sourceWidth,
            height: sourceHeight,
          })}
      </p>
    </div>
  );
}
